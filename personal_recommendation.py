import streamlit as st
import os
import tempfile
import base64
import requests
import openai
import json
from PIL import Image

import lancedb
import uform #version 2.0.2

SYSTEM_PROMPT = f"""
  You are a world-class fashion stylist who is helping your client pick clothes for an upcoming event.

  Given information about your client's preferences, write descriptions of AT LEAST 2 articles of clothing fulfilling their requirements.
  The articles of clothing must include AT LEAST a pair of shoes and EITHER (i) a one-piece like a dress OR (ii) a top & bottom like a shirt and jeans.
  Limit the number of accessories like sunglasses, hats, scarves, bags etc. to 2.
  Provide your output in JSON format, with each article of clothing as its own key.

  Here is an example:
  *******
  [Client Information]:
  Your Female client will be attending a Wedding.
  They like the Classic look, in Black,
  with Floral patterns, and especially admires pieces from Hugo Boss.

  [Clothing Descriptions]:
  ```json
    {{
      "one-piece": "A long, flowy navy blue dress with floral sequins on the waist.",
      "shoes" : "A pair of white heels with a back strap.",
      "accessories": "A black clasp with gold accents."
    }}
  ```
  *******

  Reply with JSON. No code block.
"""

# QUERY = "blue hats"
# IMG_QUERY = "images/blue_hat.jpg" # example

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# Connect to the database
uri = "data/lancedb"
db = lancedb.connect(uri)

# Connect to the table
tbl = db.open_table("poc")

# OpenAI API Key
api_key = st.secrets["OPENAI_API_KEY"]

def style_assessment_text():
    st.subheader("Tell us more about yourself!")
    st.session_state["gender"] = st.radio("What gender are you?", ["Male", "Female"])
    st.session_state["style_description"] = st.selectbox("How would you describe your personal style?", ["Classic", "Modern", "Bohemian", "Sporty"])
    st.session_state["colors"] = st.text_input("Are there any specific colors you enjoy wearing?")
    st.session_state["patterns"] = st.selectbox("Do you prefer any specific patterns?", ["Striped", "Floral", "Solid Colored", "Metallic"])
    st.session_state["icons_designers"] = st.text_input("Are there any fashion icons or designers whose aesthetic resonates with you?")
    st.session_state["outfit_occasions"] = st.selectbox("Are there any specific events or occasions for which you need outfit recommendations?", ["Conference", "Networking Event", "Wedding", "Gala", "Friend's Gathering"])

def style_assessment_image():
    st.subheader("Upload an image")
    # give user a way to upload an image of preferred outfit
    uploaded_file = st.file_uploader("Eg: share your preferred fashion style via a picture of Kate Middleton", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.read())
            st.image(temp_file.name, caption='Uploaded Image', width=200)
            st.write("Image Uploaded Successfully!")
            st.session_state["image"] = temp_file.name
            base64_image = encode_image(temp_file.name)
            return base64_image

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

@st.cache_resource 
def openai_image_analysis(base64_image):
    # OpenAI API Key
    api_key = st.secrets["OPENAI_API_KEY"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
                        You are a world-class fashion stylist like Karla Welch(https://www.instagram.com/karlawelchstylist/?hl=en)
                        Label the clothing item in the image by their category, gender and occasion.
                        Provide your output and keep to this format, with the following keys
                        (1) description
                        (2) category
                        (3) gender
                        (4) occasion.

                        Here are the possible values for each key.
                        (1) description, which is a string that describes details on style (classic, modern, sporty, etc), colors, patterns (stripes, floral, etc), accessories (necklace, earrings, head dress, etc)
                        (2) category: ['top', 'bottom', 'one piece', 'outerwear', 'shoes', 'accessories', 'hats']
                        (3) gender: ['male', 'female', 'unisex']
                        (4) occasion: ['work', 'leisure', 'formal']

                        Each key can ONLY contain one string value.

                        Always reply with one JSON item. No code block.
            """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    },
                ]
            }
        ],
        "max_tokens": 1000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # return response.json()
    # Parse the JSON string
    # data = json.loads(response)

    # Access the contents
    contents = response.json()['choices'][0]['message']['content']

    return json.loads(contents)
    # return response['choices'][0]['message']['content']

# generate a text as a consultation to the user
@st.cache_resource
def generate_recommendation(user_input, results):
    api_key = st.secrets["OPENAI_API_KEY"]

    client = openai.OpenAI(api_key=api_key)

    message_text = [
        {
            "role": "system",
            "content": """Your role is to be a trusted fashion stylist.
            Given the context of user inputs, write a paragraph to explain fashion choice by the user, and give context on what he or she might like.
            Then, generate the explanations of the results (which is stored in a df), unpack the output, and help user understands how he or she may like to wear the clothes.
            Use a tone like a best friend to the user, write a short paragraph to give context on what he or she might like.
            For example: 
            There are the items you may like based on the style of your choice. The first item, can be worn as a leisure wear, featuring a white color that resonates with your dress's base tone. It could pair well with similar skirts or pants for a cohesive look. 
            The second and third items introduce multi-color options, and can be worn as a leisure wear or a work wear. These choices suggest a blend of versatility and a subtle nod to your liking for floral or patterned designs, offering alternatives that could diversify your wardrobe while staying true to your aesthetic. 
            The color schemes and occasions these items are suited for indicate a range of possibilities for mixing and matching with your existing pieces, encouraging a playful yet refined approach to everyday dressing.
            """
        },
        {
            "role": "user",
            "content": f"[User input]\n{user_input}\
            [Returned results]\n{results}",
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=message_text,
        temperature=0,
        max_tokens=300,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )
    # return response['choices'][0]['message']['content']
    return response.choices[0].message.content


def generate_user_input(session_state):
    user_input = {
            "Description": session_state.get("style_description", ""),
            "Colors": session_state.get("colors", ""),
            "Patterns": session_state.get("patterns", ""),
            "Gender": session_state.get("gender", ""),
            "Icons/Designers": session_state.get("icons_designers", ""),
            "Outfit Occasions": session_state.get("outfit_occasions", "")
    }
    return user_input

def main():
    st.title("StyleSync: Your Style Companion")
    # initialize_session_state()  # Initialize session state at the start of main()
    tab1, tab2 = st.tabs(["Upload an example", "Use a style assessment"])
    
    with tab1:
        base64_image = style_assessment_image()
        if st.button("Save") and base64_image is not None:
            response = openai_image_analysis(base64_image)
            # st.json(response)
            # perform the search here
            # Get the embeddings of the query
            text_data = processor.preprocess_text(response['description'])
            text_embedding = model.encode_text(text_data).flatten()

            # Query the database using the given text among the hats category
            search_results = tbl.search(text_embedding).limit(3).to_pandas()
            # st.dataframe(search_results)

            # Get the embeddings of the images
            image = Image.open(st.session_state["image"])
            image_data = processor.preprocess_image(image)
            img_embeddings = model.encode_image(image_data).flatten()

            # Query the database using the given image among the shoes
            search_results_2 = tbl.search(text_embedding).limit(3).to_pandas()
            # st.dataframe(search_results_2)


            col1 = st.columns(3)
            for index, row in search_results_2.iterrows():
                filename = row["file_name"]
                image_path = "images/" + filename  
                try:
                    image = Image.open(image_path)
                    with col1[index % 3]:
                        st.image(image, caption=f"Image {index}", width=150)
                    
                except FileNotFoundError:
                    st.error(f"Image file not found for row {index}.")
            # need to return a generated description
            recommendation = generate_recommendation(response['description'], search_results)
            st.markdown(recommendation)

    with tab2:
        style_assessment_text()
        if st.button("Submit"):
            client = openai.OpenAI(api_key=api_key)
            text_input = generate_user_input(st.session_state)
            input_prompt = f"""
            [Client Information]:
            Your {text_input["Gender"]} client will be attending a {text_input["Outfit Occasions"]}.
            They like the {text_input["Description"]} look, in {text_input["Colors"]},
            with {text_input["Patterns"]}, and especially admires pieces from {text_input["Icons/Designers"]}.
            """
            try:
                response = client.chat.completions.create(
                                model="gpt-4-0125-preview",
                                messages=[
                                    {"role": "system", "content": SYSTEM_PROMPT},
                                    {"role": "user", "content": input_prompt}],
                                max_tokens=700,
                            )
                output = response.choices[0].message.content
                output = json.loads(output)
            except Exception as e:
                st.error(f"An error occurred: {e}")
            for key, value in output.items():
                text_data = processor.preprocess_text(value)
                text_embedding = model.encode_text(text_data).flatten()
                search_results = tbl.search(text_embedding).where(f"category == '{key}'", prefilter=True).limit(3).to_pandas()
                if len(search_results) > 0:
                    col = st.columns(3)
                    for index, row in search_results.iterrows():
                        filename = row["file_name"]
                        image_path = "images/" + filename
                        try:
                            image = Image.open(image_path)
                            with col[index % 3]:
                                st.image(image, caption=f"Image {index}", width=150)
                        except FileNotFoundError:
                            st.error(f"Image file not found for row {index}.")
                    recommendation = generate_recommendation(text_data, search_results)
                    st.markdown(recommendation)
                else:
                    st.write(f"Unfortunately, we don't have any pieces similar to {value}.")
            
if __name__ == "__main__":
    main()

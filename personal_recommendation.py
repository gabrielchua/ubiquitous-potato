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
    st.subheader("More information about your style")
    st.session_state["style_description"] = st.selectbox("How would you describe your personal style?", ["Classic", "Modern", "Bohemian", "Sporty"])
    st.session_state["colors"] = st.text_input("Are there any specific colors you enjoy wearing?")
    st.session_state["patterns"] = st.selectbox("Do you prefer any specific patterns?", ["Stripes", "Floral", "Solid Colors", "Metallic"])
    st.session_state["style_preference"] = st.radio("Do you prefer classic, timeless pieces or more trend-forward styles?", ["Classic / Timeless", "Trendy"])
    st.session_state["icons_designers"] = st.text_input("Are there any fashion icons or designers whose aesthetic resonates with you?")
    st.session_state["outfit_occasions"] = st.multiselect("Are there any specific events or occasions for which you need outfit recommendations?", ["Conference", "Meeting", "Networking Event"])

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
            "content": f"[User image]\n{user_input}\
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
        "Text Style Assessment": {
            "Image Style Assessment": {
                "Image": session_state.get("Uploaded Image", ""),
                
            },
            "Personal Style": {
                "Description": session_state.get("style_description", ""),
                "Colors": session_state.get("colors", ""),
                "Patterns": session_state.get("patterns", ""),
                "Style Preference": session_state.get("style_preference", ""),
                "Icons/Designers": session_state.get("icons_designers", ""),
                "Outfit Occasions": session_state.get("outfit_occasions", [])
            }
        }
    }
    return user_input

def main():
    st.title("StyleSync: Your Style Companion")
    # initialize_session_state()  # Initialize session state at the start of main()
    tab1, tab2 = st.tabs(["Upload an example", "More info"])
    
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
            pass



    
    
       
if __name__ == "__main__":
    main()

"""
app.py
"""
import base64
import json
import tempfile
import time
from PIL import Image

import lancedb
import requests
import streamlit as st
import uform #version 2.0.2
from openai import OpenAI

from config import (
    EXTRACT_IMG_META_DATA,
    IMG_BASE_URL,
    GENERATE_DESC_BASED_ON_PREFERENCES,
    GENERATE_DESC_BASED_ON_NEGATIVE_PREFERENCES,
    GENERATE_STYLE_RECOMMENDATION,
    GPT3_5_TURBO,
    GPT4,
    GPT4_VISION,
    LANCEDB_TABLE_NAME,
    LANCEDB_URI,
    OPENAI_API_KEY,
    )

# Set the page configuration
st.set_page_config(page_title="StyleSync", page_icon="👗")

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# Connect to the database and table
db = lancedb.connect(LANCEDB_URI)
tbl = db.open_table(LANCEDB_TABLE_NAME)

# Initialise the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def style_assessment_text():
    """ Streamlit component to collect user input for style assessment."""
    st.subheader("Tell us more about yourself!")
    st.session_state["gender"] = st.radio("What is your gender?", ["Male", "Female"])
    st.session_state["outfit_occasions"] = st.selectbox("Any specific events or occasions for which you need outfit recommendations for?", ["Conference", "Networking Event", "Wedding", "Gala", "Friend's Gathering"])
    sub1, sub2 = st.tabs(["What I like", "What I hate"])
    with sub1:
        st.session_state["style_description"] = st.selectbox("Describe your personal style?", ["Classic", "Modern", "Bohemian", "Sporty"])
        st.session_state["colors"] = st.text_input("Any specific colors you enjoy wearing?")
        st.session_state["patterns"] = st.selectbox("Any specific patterns your prefer?", ["Striped", "Floral", "Solid Colored", "Metallic"])
        st.session_state["icons_designers"] = st.text_input("Fashion icons or designers whose aesthetic resonates with you?")
        st.session_state["variant"] = "like"
    with sub2:
        st.session_state["style_description"] = st.selectbox("What style would you never be caught wearing?", ["Classic", "Modern", "Bohemian", "Sporty"])
        st.session_state["colors"] = st.text_input("Any specific colors you don't like?")
        st.session_state["patterns"] = st.selectbox("How about patterns you avoid?", ["Striped", "Floral", "Solid Colored", "Metallic"])
        st.session_state["variant"] = "hate"

def style_assessment_image():
    """ Streamlit component to upload an image for style assessment. """
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
    """ Encode an image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@st.cache_resource
def openai_image_analysis(base64_image):
    """ Perform image analysis using OpenAI's API. """

    input_prompt = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}", "detail": "low"}}]

    message_list = [
        {"role": "system","content": EXTRACT_IMG_META_DATA},
        {"role": "user", "content": input_prompt},
    ]

    response = client.chat.completions.create(
        model=GPT4_VISION,
        messages=message_list,
        max_tokens=500,
        temperature=0,
        seed=0
    )
    
    tagged_data = response.choices[0].message.content
    tagged_data = json.loads(tagged_data)

    return tagged_data

# generate a text as a consultation to the user
# @st.cache_resource
def generate_recommendation(user_input, results, st_container):
    """ Generate a streamed recommendation based on the user input and the results. """

    message_list = [
        {"role": "system","content": GENERATE_STYLE_RECOMMENDATION},
        {"role": "user", "content": f"[User input]\n{user_input}\n\n[Returned results]\n{results}",},
    ]

    stream = client.chat.completions.create(
        model=GPT3_5_TURBO,
        messages=message_list,
        temperature=0.1,
        seed=0,
        stream=True
    )

    text = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text_chunk = chunk.choices[0].delta.content
            for char in text_chunk:
                text += char
                st_container.info(text)

def generate_user_input(session_state):
    """ Generate user input based on the session state."""
    user_input = {
            "Description": session_state.get("style_description", ""),
            "Colors": session_state.get("colors", ""),
            "Patterns": session_state.get("patterns", ""),
            "Gender": session_state.get("gender", ""),
            "Icons/Designers": session_state.get("icons_designers", ""),
            "Outfit Occasions": session_state.get("outfit_occasions", "")
    }
    return user_input

def download_image(file_name):
    """ Download an image from a given URL. """
    full_url = f"{IMG_BASE_URL}{file_name}"
    response = requests.get(full_url)
    return response.content
    
def main():
    """ Main function for the Streamlit app. """
    st.title("StyleSync: Your Style Companion")
    # initialize_session_state()  # Initialize session state at the start of main()
    tab1, tab2 = st.tabs(["Upload an example", "Use a style assessment"])
    
    with tab1:
        base64_image = style_assessment_image()
        if st.button("Save") and base64_image is not None:
            response = openai_image_analysis(base64_image)

            # Get the embeddings of the image description
            text_data = processor.preprocess_text(response['description'])
            text_embedding = model.encode_text(text_data).flatten()

            # Query the database using the given text among the hats category
            search_results_text = tbl.search(text_embedding).limit(3).to_pandas()

            # Get the embeddings of the image
            image = Image.open(st.session_state["image"])
            image_data = processor.preprocess_image(image)

            # Query the database using the given image among the shoes
            search_results_img = tbl.search(image_data).limit(3).to_pandas()

            retrieved_img_file_names = list(set(search_results_img["file_name"].unique()) + set(search_results_text["file_name"].unique()))
            retrieved_img_file_names = retrieved_img_file_names[:3]
 
            col1 = st.columns(3)
            # for index, row in search_results_img.iterrows():
                # filename = row["file_name"]
            for index, filename in enumerate(retrieved_img_file_names):
                try:
                    # image = Image.open(image_path)
                    with col1[index % 3]:
                        st.image(download_image(filename), caption=f"Image {index + 1}", width=150)
                except FileNotFoundError:
                    st.error(f"Image file not found for row {index}.")

            # Based on these images, generate a recommendation
            recommendation_box = st.empty()
            generate_recommendation(response['description'], search_results_img, recommendation_box)

    with tab2:
        style_assessment_text()
        if st.button("Submit"):
            text_input = generate_user_input(st.session_state)
            variant = st.session_state.get("variant", "")

            preferences = f"""
                [Client Information]:
                Your {text_input["Gender"]} client will be attending a {text_input["Outfit Occasions"]}.
                They like the {text_input["Description"]} look, in {text_input["Colors"]},
                with {text_input["Patterns"]}, and especially admires pieces from {text_input["Icons/Designers"]}.
            """

            negative_preferences = f"""
                [Client Information]:
                Your {text_input["Gender"]} client will be attending a{text_input["Outfit Occasions"]}.
                They DO NOT like the {text_input["Description"]} look, {text_input["Colors"]} colours and {text_input["Patterns"]}.
            """

            try:
                message_list = [
                    {"role": "system","content": GENERATE_DESC_BASED_ON_PREFERENCES if variant == "like" else GENERATE_DESC_BASED_ON_NEGATIVE_PREFERENCES},
                    {"role": "user", "content": preferences if variant == "like" else negative_preferences},
                ]

                response = client.chat.completions.create(
                                model=GPT4,
                                messages=message_list,
                                max_tokens=700,
                                temperature=0.1,
                                seed=0
                            )
                output = response.choices[0].message.content
                output = json.loads(output)
            except Exception as e:
                st.error(f"An error occurred: {e}")
            for key, value in output.items():
                st.markdown(f"**Similar to _'{value.capitalize()}'_**")
                
                text_data = processor.preprocess_text(value)
                text_embedding = model.encode_text(text_data).flatten()

                # search_results = tbl.search(text_embedding).where(f"category == '{key}'", prefilter=True).limit(3).to_pandas()
                search_results = tbl.search(text_embedding).limit(3).to_pandas()
                if len(search_results) > 0:
                    col = st.columns(3)
                    for index, row in search_results.iterrows():
                        filename = row["file_name"]
                        try:
                            with col[index % 3]:
                                st.image(download_image(filename), caption=f"Image {index + 1}", width=150)
                        except FileNotFoundError:
                            st.error(f"Image file not found for row {index}.")
                    recommendation_box_2 = st.empty()
                    generate_recommendation(text_data, search_results, recommendation_box_2)
                else:
                    st.info(f"Unfortunately, we don't have any similar pieces. We are working to expanding our dataset. Please check back later. ")
            
if __name__ == "__main__":
    main()

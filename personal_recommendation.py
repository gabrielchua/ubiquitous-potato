import streamlit as st
import os
import tempfile
import code as cd

def style_assessment_text():
    st.subheader("More information about your style")
    st.session_state["style_description"] = st.selectbox("How would you describe your personal style?", ["Classic", "Modern", "Bohemian", "Sporty"])
    st.session_state["colors"] = st.text_input("Are there any specific colors you enjoy wearing?")
    st.session_state["patterns"] = st.selectbox("Do you prefer any specific patterns?", ["Stripes", "Floral", "Solid Colors", "Metallic"])
    st.session_state["style_preference"] = st.radio("Do you prefer classic, timeless pieces or more trend-forward styles?", ["Classic / Timeless", "Trendy"])
    st.session_state["icons_designers"] = st.text_input("Are there any fashion icons or designers whose aesthetic resonates with you?")
    st.session_state["outfit_occasions"] = st.multiselect("Are there any specific events or occasions for which you need outfit recommendations?", ["Conferences", "Meetings", "Networking Events"])

def style_assessment_image():
    st.subheader("Upload an image")
    # give user a way to upload an image of preferred outfit
    uploaded_file = st.file_uploader("Eg: share your preferred fashion style via a picture of Kate Middleton", type=["jpg", "png", "jpeg"])

    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.read())
            st.image(temp_file.name, caption='Uploaded Image', use_column_width=True)
            st.write("Image Uploaded Successfully!")
            os.unlink(temp_file.name)
        # save_image_path = os.path.join('uploaded_images', uploaded_file.name)
        
        # # Create 'uploaded_images' directory if it does not exist
        # if not os.path.exists('uploaded_images'):
        #     os.makedirs('uploaded_images')

        # # Write the image to the filesystem
        # with open(save_image_path, "wb") as f:
        #     f.write(uploaded_file.getbuffer())
        
        # st.image(uploaded_file, caption='Uploaded Image.', use_column_width=True)
        # st.success("Image uploaded and saved successfully!")
        # st.write(f"Image file saved at: {save_image_path}")
    
# def body_type_fit():
#     st.subheader("Body Type and Fit")
#     st.session_state["body_type"] = st.text_input("How would you describe your body type?")
#     st.session_state["body_areas"] = st.text_input("Are there any areas you prefer to highlight or camouflage?")
#     st.session_state["fit_preference"] = st.selectbox("Do you have any specific fit or silhouette preferences when it comes to clothing?", ["Fitted", "Loose", "Tailored"])
#     st.session_state["comfort_mobility"] = st.multiselect("Are there any comfort or mobility considerations we should keep in mind when selecting pieces for you?", ["Comfortable fabrics", "Stretchy materials"])

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
    st.title("Fashion Emulator")
    # initialize_session_state()  # Initialize session state at the start of main()
    tab1, tab2 = st.tabs(["Upload an example", "More info"])
    
    with tab1:
        style_assessment_image()
    with tab2:
        style_assessment_text()

    # save settings into 
    if st.button("Save"):
        # use the extraction 

        st.json(user_input)
       

if __name__ == "__main__":
    main()

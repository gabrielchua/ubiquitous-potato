import json
import base64
import os
import streamlit as st
import requests
import pandas as pd
import random
import time

# from openai import OpenAI

MODEL_NAME = "gpt-4-vision-preview"
api_key=st.example-secrets("OPENAI_API_KEY")

def get_base64_string(imge_file_path:str) -> str:
    with open(imge_file_path, "rb") as image_file:
      return base64.b64encode(image_file.read()).decode('utf-8')

def add_dict_to_dataframe(input_dict, dataframe):
    new_row = pd.DataFrame([input_dict])
    dataframe = pd.concat([dataframe, new_row], ignore_index=True)
    return dataframe

file_names_all = [f for f in os.listdir('images') if f.endswith('.jpg') or f.endswith('.png')]
random.shuffle(file_names_all)
file_names = file_names_all[:500]

df = pd.DataFrame(columns=['file_name', 'category', 'gender', 'occasion'])

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

# for loop to handle all images
for img_file in file_names:
  base64_image = get_base64_string(f"images/{img_file}")
  payload = {
    "model": MODEL_NAME,
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": f"""
              You are a world-class fashion stylist.
              Label the clothing item in the image by their category, gender and occasion.
              Provide your output in JSON format with the keys:
              (1) category
              (2) gender
              (3) occasion.

              Here are the possible values for each key.
              (1) category: ['top', 'bottom', 'top & bottom', 'outerwear', 'shoes', 'accessories', 'hats']
              (2) gender: ['male', 'female', 'unisex']
              (3) occasion: ['work', 'leisure', 'formal']

              Each key can ONLY contain one string value.

              Always reply with JSON. No code block.

              Reply with JSON. No code block.
            """
          },
          {
            "type": "image_url",
            "image_url": {
              "url": f"data:image/jpeg;base64,{base64_image}"
            }
          }
        ]
      }
    ],
    "max_tokens": 300
  }
  try:
    print("Getting response from OpenAI for ", img_file)
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    output = json.loads(response.json()["choices"][0]["message"]["content"])
    output['file_name'] = img_file
    df = add_dict_to_dataframe(output, df)
    print("Done for ", img_file)
    time.sleep(0.5)
  except Exception as e:
    print(e)
    print(f"Error for {img_file}, writing intermediate file to csv")
    df.to_csv('output.csv', index=False)

print("All files done! Exporting to csv...")
df.to_csv('output.csv', index=False)

"""
app.py
"""

# Third-party imports
import lancedb
import streamlit as st
import uform #version 2.0.2

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# Connect to the database
uri = "data/lancedb"
db = lancedb.connect(uri)

# Connect to the table
tbl = db.open_table("poc")


query = st.text_input("Enter a search query")

if query:
    text_data = processor.preprocess_text(query)
    _, text_embedding = model.encode_text(text_data, return_features=True)
    results = tbl.search(text_embedding.flatten()).limit(2).to_pandas(flatten=True)

images = results["name"].tolist()
for img in images:
    st.image(f"images/{img}")

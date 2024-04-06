"""
ingest_data.py
"""
# Standard library imports
import os
from PIL import Image # type: ignore

# Third-party imports
import lancedb #
import pyarrow as pa #
import uform #version 2.0.2

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# Connect to the database
uri = "data/lancedb"
db = lancedb.connect(uri)

# Create a schema and empty table
schema = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), list_size=256)),
    pa.field("name", pa.string())
    ])
tbl = db.create_table("poc", schema=schema)

# Get all .jpg or .png files in the 'images' directory
file_names = [f for f in os.listdir('images') if f.endswith('.jpg') or f.endswith('.png')]

for img_file_name in file_names:
    image = Image.open(f"images/{img_file_name}")
    image_data = processor.preprocess_image(image)
    _, image_embedding = model.encode_image(image_data, return_features=True)
    img_data_to_add = [
        {
            "vector": image_embedding.flatten(),
            "name": f"{img_file_name}"
        },
    ]
    tbl.add(img_data_to_add) # Add the image embedding to the table

# Create index
# tbl.create_index(num_sub_vectors=1)

# Query the table

text = "red shoes"
text_data = processor.preprocess_text(text)
_, text_embedding = model.encode_text(text_data, return_features=True)
tbl.search(text_embedding.flatten()).limit(2).to_pandas(flatten=True)

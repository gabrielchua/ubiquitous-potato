"""
ingest_data.py
"""
# Standard library imports
import os
from PIL import Image # type: ignore

# Third-party imports
import lancedb
import pandas as pd
import pyarrow as pa
import uform #version 2.0.2
from tqdm import tqdm

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# # Load the data
# df = pd.read_csv('../data/meta_data.csv')

# Connect to the database
uri = "../data/lancedb"
db = lancedb.connect(uri)

# # Create a schema
schema = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), list_size=256)),
    pa.field("file_name", pa.string()),
    # pa.field("category", pa.string()),
    # pa.field("gender", pa.string()),
    # pa.field("occasion", pa.string()),
    # pa.field("color", pa.string()),
    ])

# # Create an empty table with the schema
tbl = db.create_table("poc_2", schema=schema)


# # Get all .jpg or .png files in the 'images' directory
file_names_all = [f for f in os.listdir('../images/images') if f.endswith('.jpg') or f.endswith('.png')]

# Iterate over the rows in the dataframe
# for index, row in tqdm(df.iterrows(), total=len(df)):
for file_name in tqdm(file_names_all):
    # image = Image.open(f"../images/images/{row['file_name']}")
    image = Image.open(f"../images/images/{file_name}")
    image_data = processor.preprocess_image(image)
    _, image_embedding = model.encode_image(image_data, return_features=True)
    img_data_to_add = [
        {
            "vector": image_embedding.flatten(),
            "file_name": f"{file_name}",
            # "category": f"{row['category']}",
            # "gender": f"{row['gender']}",
            # "occasion": f"{row['occasion']}",
            # "color": f"{row['color']}"
        },
    ]
    tbl.add(img_data_to_add) # Add the image and metadata to the table

# Create index
# tbl.create_index(num_sub_vectors=1)

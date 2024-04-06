import lancedb
import uform #version 2.0.2

QUERY = "blue hats"
IMG_QUERY = "images/blue_hat.jpg" # example

# Load the model
model, processor = uform.get_model_onnx('unum-cloud/uform-vl-english-small', 'cpu', 'fp32')

# Connect to the database
uri = "data/lancedb"
db = lancedb.connect(uri)

# Connect to the table
tbl = db.open_table("poc")

# Get the embeddings of the query
text_data = processor.preprocess_text(QUERY)
text_embedding = model.encode_text(text_data).flatten()

# Query the database using the given text among the hats category
search_results = tbl.search(text_embedding).where("category == 'hats'", prefilter=True).limit(3).to_pandas()

# Get the embeddings of the images
image_data = processor.preprocess_image(IMG_QUERY)
img_embeddings = model.encode_image(image_data).flatten()

# Query the database using the given image among the shoes
search_results = tbl.search(text_embedding).where("category == 'shoes'", prefilter=True).limit(3).to_pandas()

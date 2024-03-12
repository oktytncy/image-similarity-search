import os
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from PIL import Image
from sentence_transformers import SentenceTransformer
from getpass import getpass

# Connection variables
SECURE_CONNECT_BUNDLE_PATH = 'conf/secure-connect.zip'

ASTRA_DB_TOKEN_BASED_PASSWORD =  '<secret>'
ASTRA_CLIENT_ID = '<clientId>'
ASTRA_DB_KEYSPACE = "<keyspace_name>"
TABLE_NAME = '<table_name>'

ASTRA_CLIENT_SECRET = ASTRA_DB_TOKEN_BASED_PASSWORD
KEYSPACE_NAME = ASTRA_DB_KEYSPACE

# Connect to Astra DB
cloud_config = {'secure_connect_bundle': SECURE_CONNECT_BUNDLE_PATH}

auth_provider = PlainTextAuthProvider(ASTRA_CLIENT_ID, ASTRA_CLIENT_SECRET)
cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider, protocol_version=4)
session = cluster.connect()

# Drop / Create Schema
print(f"Creating table {TABLE_NAME} in keyspace {KEYSPACE_NAME}")
session.execute(f"CREATE TABLE IF NOT EXISTS {KEYSPACE_NAME}.{TABLE_NAME} (id int PRIMARY KEY, name TEXT, description TEXT, item_vector VECTOR<FLOAT, 512>)")

# SAI (storage attached index) indexes creation
# This index is optimized for certain types of queries, such as nearest neighbor searches.
print(f"Creating index image_ann_index on table {TABLE_NAME} and inserting example data")
session.execute(f"CREATE CUSTOM INDEX IF NOT EXISTS image_ann_index ON {KEYSPACE_NAME}.{TABLE_NAME}(item_vector) USING 'StorageAttachedIndex'")

print(f"Truncate table {TABLE_NAME} in keyspace {KEYSPACE_NAME}")
session.execute(f"TRUNCATE TABLE {KEYSPACE_NAME}.{TABLE_NAME}")

# Load CLIP model
# CLIP models are multimodal, and capable of understanding both text and images.
# For more details, https://huggingface.co/sentence-transformers/clip-ViT-B-32 or https://github.com/openai/CLIP
model = SentenceTransformer('clip-ViT-B-32')

# Load images
image_dir = 'images'
image_files = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]

image_data = []
id_counter = 1  # Start the ID counter

for filename in image_files:
    image_path = os.path.join(image_dir, filename)
    name = os.path.splitext(filename)[0]  # Remove the file extension from the name
    description = f"description{id_counter}"  # Set the description based on the ID counter
    
    # If storing vector embeddings
    # Encodes each image into a vector embedding using the CLIP model
    img_emb = model.encode(Image.open(image_path))

    # Embeddings are converted to a list (item_vector) to be stored in the database.   
    item_vector = img_emb.tolist()
    
    # If you intend to store raw image data, you need a different approach
    # with open(image_path, 'rb') as img_file:
    #     item_vector = img_file.read()  # This will read the image as binary data
    image_data.append((id_counter, name, description, item_vector))
    
    # Execute the insert statement for each image

    session.execute(f"INSERT INTO {KEYSPACE_NAME}.{TABLE_NAME} (id, name, description, item_vector) VALUES (%s, %s, %s, %s)", (id_counter, name, description, item_vector))
    
    id_counter += 1  # Increment the ID counter

query_string = "ballistic analysis"
text_emb = model.encode(query_string)
print(f"model provided embeddings for the string: 'ballistic analysis': {text_emb.tolist()}")

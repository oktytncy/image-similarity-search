from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from PIL import Image
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer

# Connection variables
SECURE_CONNECT_BUNDLE_PATH = 'conf/secure-connect.zip'

ASTRA_DB_TOKEN_BASED_PASSWORD =  '<secret>'
ASTRA_CLIENT_ID = '<clientId>'
ASTRA_DB_KEYSPACE = "<keyspace_name>"
TABLE_NAME = '<table_name>'

ASTRA_CLIENT_SECRET = ASTRA_DB_TOKEN_BASED_PASSWORD
KEYSPACE_NAME = ASTRA_DB_KEYSPACE

# Set up the authentication provider and cluster connection
auth_provider = PlainTextAuthProvider(ASTRA_CLIENT_ID, ASTRA_CLIENT_SECRET)
cloud_config = {'secure_connect_bundle': SECURE_CONNECT_BUNDLE_PATH}
cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider, protocol_version=4)
session = cluster.connect(KEYSPACE_NAME)

# Load the model used for encoding images
model = SentenceTransformer('clip-ViT-B-32')

# Function to encode an image using the model
def encode_image(image_path):
    img = Image.open(image_path)
    img_emb = model.encode([img])[0]  # Ensure the image is passed in a list
    return img_emb

# Function to calculate cosine similarity -- added in v2
# A function calculate_similarity(vector1, vector2) computes the cosine similarity between two vectors.
def calculate_similarity(vector1, vector2):
    vector1 = np.array(vector1).reshape(1, -1)
    vector2 = np.array(vector2).reshape(1, -1)
    return cosine_similarity(vector1, vector2)[0][0]

# Load a single PNG file from the suspicious folder
suspicious_folder = 'suspicious'
suspicious_files = [f for f in os.listdir(suspicious_folder) if f.endswith('.png')]

N = 1  # or any other integer value you wish to set as the limit

if suspicious_files:
    suspicious_image_path = os.path.join(suspicious_folder, suspicious_files[0])
    suspicious_vector = encode_image(suspicious_image_path)

    # Perform ANN(Approximate nearest neighbor) search to find the most similar image in the database
    query = f"SELECT id, name, item_vector FROM {KEYSPACE_NAME}.{TABLE_NAME} ORDER BY item_vector ANN OF {suspicious_vector.tolist()} LIMIT {N}"
    row = session.execute(query).one()

    if row:
        name, description, item_vector = row
        similarity_score = calculate_similarity(suspicious_vector, item_vector)

        # Display the suspicious image
        fig, ax = plt.subplots(figsize=(5, 5))
        suspicious_img = Image.open(suspicious_image_path)
        ax.imshow(suspicious_img)
        ax.set_title('Suspicious Image')
        ax.axis('off')
        
        # Display information about the most similar image -- updated in v2
        plt.figtext(0.5, 0.01, f'Most Similar Image: {name}\nDescription: {description}\nSimilarity Score: {similarity_score:.4f}', ha="center", fontsize=12, bbox={"facecolor":"orange", "alpha":0.5, "pad":5})
        plt.show()
    else:
        print("No similar images found in the database.")
else:
    print("No PNG files found in the suspicious folder.")
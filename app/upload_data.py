import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
INPUT_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
input_container = blob_service.get_container_client(INPUT_CONTAINER)

LOCAL_DATA_DIR = "data"  

def upload_local_data():
    for root, _, files in os.walk(LOCAL_DATA_DIR):
        for file in files:
            if file.lower().endswith(".pdf"):
                local_path = os.path.join(root, file)
                
                relative_path = os.path.relpath(local_path, LOCAL_DATA_DIR).replace("\\", "/")
                print(f"Uploading {local_path} → {INPUT_CONTAINER}/{relative_path}")
                with open(local_path, "rb") as f:
                    input_container.upload_blob(name=relative_path, data=f, overwrite=True)

if __name__ == "__main__":
    upload_local_data()

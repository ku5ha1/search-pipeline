import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
if not connect_str:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING not found in environment")

container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
if not container_name:
    raise ValueError("CONTAINER NAME not found in environment")

blob_service_client = BlobServiceClient.from_connection_string(connect_str)

container_client = blob_service_client.get_container_client(container_name)

try:
    print(f"Listing blobs in container '{container_name}':")
    blob_list = container_client.list_blobs()
    for blob in blob_list:
        print("\t" + blob.name)

except Exception as ex:
    print("Exception:")
    print(ex)

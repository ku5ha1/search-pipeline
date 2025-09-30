import os
import json
import requests
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not STORAGE_CONN_STR:
    raise ValueError("STORAGE_CONN_STR not found")

INPUT_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
if not INPUT_CONTAINER:
    raise ValueError("INPUT_CONTAINER not found")

OUTPUT_CONTAINER = os.getenv("AZURE_STORAGE_OUTPUT_CONTAINER_NAME")
if not OUTPUT_CONTAINER:
    raise ValueError("OUTPUT_CONTAINER not found")

DOCINT_ENDPOINT = os.getenv("DOCINT_ENDPOINT")
DOCINT_KEY = os.getenv("DOCINT_KEY")
if not DOCINT_ENDPOINT or not DOCINT_KEY:
    raise ValueError("DOCINT_ENDPOINT or DOCINT_KEY not found in environment")

blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
input_container = blob_service.get_container_client(INPUT_CONTAINER)
output_container = blob_service.get_container_client(OUTPUT_CONTAINER)
docint_client = DocumentIntelligenceClient(DOCINT_ENDPOINT, AzureKeyCredential(DOCINT_KEY))

def ocr_pdf_bytes(pdf_bytes: bytes) -> dict:
    stream = BytesIO(pdf_bytes)
    poller = docint_client.begin_analyze_document("prebuilt-read", stream)
    result = poller.result()

    structured_result = {"pages": []}
    for page in result.pages:
        page_text = "\n".join([line.content for line in page.lines])
        structured_result["pages"].append({
            "page_number": page.page_number,
            "content": page_text,
            "lines": [{"text": line.content, "polygon": line.polygon} for line in page.lines]
        })

    return structured_result

def process_blob(pdf_blob_name: str):
    try:
        print(f"Processing in background: {pdf_blob_name}")

        pdf_bytes = input_container.download_blob(pdf_blob_name).readall()

        ocr_result = ocr_pdf_bytes(pdf_bytes)
        
        json_path = pdf_blob_name.replace(".pdf", ".json")

        output_container.upload_blob(
            name=json_path,
            data=json.dumps(ocr_result, ensure_ascii=False, indent=2),
            overwrite=True
        )
        return f"Uploaded {OUTPUT_CONTAINER}/{json_path}"
    except Exception as e:
        return f"Error processing {pdf_blob_name}: {e}"

def main():
    pdf_blobs = [b.name for b in input_container.list_blobs() if b.name.lower().endswith(".pdf")]

    if not pdf_blobs:
        print("No PDFs found in input container.")
        return

    print(f"Found {len(pdf_blobs)} PDFs. Starting background OCR...")

    results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_blob = {executor.submit(process_blob, blob): blob for blob in pdf_blobs}
        for future in as_completed(future_to_blob):
            results.append(future.result())

    print("\n--- Summary ---")
    for r in results:
        print(r)

def ocr_pdf_url(pdf_url: str) -> dict:
    r = requests.get(pdf_url)
    r.raise_for_status()
    pdf_bytes = r.content
    return ocr_pdf_bytes(pdf_bytes)

if __name__ == "__main__":
    main()


# import os
# from dotenv import load_dotenv
# from azure.storage.blob import BlobServiceClient

# load_dotenv()

# connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
# if not connect_str:
#     raise ValueError("AZURE_STORAGE_CONNECTION_STRING not found in environment")

# # Initialize blob service client
# blob_service_client = BlobServiceClient.from_connection_string(connect_str)

# # Replace with your container name
# container_name = "magazine-pdfs"
# container_client = blob_service_client.get_container_client(container_name)

# try:
#     print(f"Listing blobs in container '{container_name}':")
#     blob_list = container_client.list_blobs()
#     for blob in blob_list:
#         print("\t" + blob.name)

# except Exception as ex:
#     print("Exception:")
#     print(ex)

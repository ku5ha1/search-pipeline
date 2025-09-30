import logging
import os
from azure.storage.blob import BlobServiceClient
import azure.functions as func
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.run_pipeline import process_issue_from_json
from app.embed import delete_existing_docs

# --- Environment ---
STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
OUTPUT_CONTAINER = os.getenv("AZURE_STORAGE_OUTPUT_CONTAINER_NAME")
FLAG_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "function-flags")
DELETE_FLAG_BLOB = "delete_done.flag"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 8)) 

if not STORAGE_CONN_STR or not OUTPUT_CONTAINER:
    raise ValueError("Missing STORAGE env vars")

blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
output_container = blob_service.get_container_client(OUTPUT_CONTAINER)
flag_container = blob_service.get_container_client(FLAG_CONTAINER)

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */5 * * * *",  
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def timer_trigger1(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    delete_flag_exists = any(b.name == DELETE_FLAG_BLOB for b in flag_container.list_blobs())
    if not delete_flag_exists:
        logging.info("Deleting existing indexed docs for the first run...")
        try:
            delete_existing_docs()
            flag_container.upload_blob(DELETE_FLAG_BLOB, b"", overwrite=True)
            logging.info("Existing docs deleted and flag created.")
        except Exception as e:
            logging.error(f"Failed to delete existing docs: {e}")

    json_blobs = [b.name for b in output_container.list_blobs() if b.name.endswith(".json")]
    logging.info(f"Found {len(json_blobs)} OCR JSON files to process.")

    def process_json(json_path):
        pdf_id = os.path.basename(json_path).replace(".json", "")
        try:
            year, month = map(int, pdf_id.split("-")[:2])
        except ValueError:
            year, month = 0, 0
        source_url = ""

        try:
            process_issue_from_json(json_path, pdf_id, year, month, source_url)
            logging.info(f"Processed {json_path}")
        except Exception as e:
            logging.error(f"Failed to process {json_path}: {e}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_json, jb) for jb in json_blobs]
        for _ in as_completed(futures):
            pass

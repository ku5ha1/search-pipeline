import os
import sys
import json
import time
from azure.storage.blob import BlobServiceClient
from app.normalize import normalize_ocr
from app.chunk import chunk_pages
from app.embed import embed_texts
from app.index_search import ensure_index, upsert_chunks
from dotenv import load_dotenv

load_dotenv()

STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
OUTPUT_CONTAINER = os.getenv("AZURE_STORAGE_OUTPUT_CONTAINER_NAME")
if not STORAGE_CONN_STR or not OUTPUT_CONTAINER:
    raise ValueError("Missing STORAGE env vars")

blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
output_container = blob_service.get_container_client(OUTPUT_CONTAINER)

json_blobs = [b.name for b in output_container.list_blobs() if b.name.endswith(".json")]
print(f"Found {len(json_blobs)} OCR JSON files")

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")
BATCH_SIZE = 16
MAX_RETRIES = 5
BACKOFF_FACTOR = 2


def embed_texts_batch(texts):
    import requests
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
        headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
        payload = {"input": batch}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                embeddings.extend([item["embedding"] for item in data["data"]])
                break  # success
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429:
                    sleep_time = BACKOFF_FACTOR ** attempt
                    print(f"[WARN] 429 Too Many Requests. Retrying in {sleep_time}s... (Attempt {attempt})")
                    time.sleep(sleep_time)
                else:
                    raise
            except Exception as e:
                print(f"[ERROR] Embedding failed: {e}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(BACKOFF_FACTOR ** attempt)
    return embeddings

def load_ocr_json_from_blob(json_path: str) -> dict:
    """Download OCR result JSON from blob container"""
    blob = output_container.download_blob(json_path)
    return json.loads(blob.readall().decode("utf-8"))


def process_issue_from_json(json_path: str, pdf_id: str, year: int, month: int, source_url: str):
    # Load OCR JSON
    doc = load_ocr_json_from_blob(json_path)

    # Normalize into pages
    pages = normalize_ocr(doc, pdf_id, year, month, source_url)

    # Chunk pages
    chunks = chunk_pages(pages)

    # Generate embeddings batch-wise with retry
    texts = [c["text"] for c in chunks if c.get("text")]
    if texts:
        embs = embed_texts_batch(texts)
        for c, e in zip(chunks, embs):
            c["embedding"] = e

        ensure_index(dim=len(embs[0]) if embs else 3072)
        upsert_chunks(chunks)
        print(f"Indexed {len(chunks)} chunks for {pdf_id}")
    else:
        print(f"No text found in chunks for {pdf_id}")

if __name__ == "__main__":
    if len(sys.argv) == 6:
        json_path, pdf_id, year, month, source_url = sys.argv[1:]
        process_issue_from_json(json_path, pdf_id, int(year), int(month), source_url)
    else:
        print("Processing all OCR JSON files in output container...")
        for json_path in json_blobs:
            pdf_id = os.path.basename(json_path).replace(".json", "")
            try:
                year, month = map(int, pdf_id.split("-")[:2])
            except ValueError:
                year, month = 0, 0
            process_issue_from_json(json_path, pdf_id, year, month, source_url="")

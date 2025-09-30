import os, sys, json
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

def load_ocr_json_from_blob(json_path: str) -> dict:
    """Download OCR result JSON from extracted-json container"""
    blob = output_container.download_blob(json_path)
    return json.loads(blob.readall().decode("utf-8"))

def process_issue_from_json(json_path: str, pdf_id: str, year: int, month: int, source_url: str):
    # Load pre-extracted OCR result
    doc = load_ocr_json_from_blob(json_path)

    # Normalize into pages
    pages = normalize_ocr(doc, pdf_id, year, month, source_url)

    # Chunk pages
    chunks = chunk_pages(pages)

    # Generate embeddings in batches
    texts = [c["text"] for c in chunks]
    embs = []
    for i in range(0, len(texts), 16):
        embs += embed_texts(texts[i:i+16])

    for c, e in zip(chunks, embs):
        c["embedding"] = e

    # Ensure index exists, use embedding size from first vector
    ensure_index(dim=len(embs[0]) if embs else 3072)

    # Push to Azure Cognitive Search
    upsert_chunks(chunks)
    print(f"Indexed {len(chunks)} chunks for {pdf_id}")

if __name__ == "__main__":
    
    if len(sys.argv) != 6:
        print("Usage: python -m app.run_pipeline <json_path> <pdf_id> <year> <month> <source_url>")
        sys.exit(1)

    json_path, pdf_id, year, month, source_url = sys.argv[1:]
    process_issue_from_json(json_path, pdf_id, int(year), int(month), source_url)

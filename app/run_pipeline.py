import os
import sys
import json
import logging
from app.ocr_ingest import ocr_pdf_url
from app.normalize import normalize_ocr
from app.chunk import chunk_pages
from app.embed import embed_texts
from app.index_search import ensure_index, upsert_chunks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", 16))

def process_issue(pdf_url: str, pdf_id: str, year: int, month: int):
    try:
        logging.info(f"Starting pipeline for {pdf_id} ({year}-{month})")

        doc = ocr_pdf_url(pdf_url)
        if not doc:
            logging.warning(f"OCR returned empty result for {pdf_id}")
            return

        pages = normalize_ocr(doc, pdf_id, year, month, pdf_url)
        if not pages:
            logging.warning(f"No pages extracted for {pdf_id}")
            return

        chunks = chunk_pages(pages)
        if not chunks:
            logging.warning(f"No chunks generated for {pdf_id}")
            return

        texts = [c["text"] for c in chunks]
        embeddings = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i:i+EMBED_BATCH_SIZE]
            try:
                embeddings += embed_texts(batch)
            except Exception as e:
                logging.error(f"Embedding failed for batch {i}-{i+len(batch)}: {e}")
                embeddings += [[0.0]*3072]*len(batch)  # fallback zero vector

        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb

        if embeddings:
            dim = len(embeddings[0])
            ensure_index(dim=dim)
            upsert_chunks(chunks)
            logging.info(f"Indexed {len(chunks)} chunks for {pdf_id}")
        else:
            logging.warning(f"No embeddings available for {pdf_id}, skipping indexing")

    except Exception as e:
        logging.error(f"Pipeline failed for {pdf_id}: {e}", exc_info=True)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        logging.error("Usage: python -m app.run_pipeline <pdf_url> <pdf_id> <year> <month>")
        sys.exit(1)

    url, pdf_id, year, month = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    process_issue(url, pdf_id, year, month)

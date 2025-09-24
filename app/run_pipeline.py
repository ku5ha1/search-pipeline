import os, json, sys
from app.ocr_ingest import ocr_pdf_url
from app.normalize import normalize_ocr
from app.chunk import chunk_pages
from app.embed import embed_texts
from app.index_search import ensure_index, upsert_chunks

def process_issue(pdf_url: str, pdf_id: str, year: int, month: int):
    doc = ocr_pdf_url(pdf_url)
    pages = normalize_ocr(doc, pdf_id, year, month, pdf_url)
    chunks = chunk_pages(pages)
    texts = [c["text"] for c in chunks]
    embs = []
    for i in range(0, len(texts), 16):
        embs += embed_texts(texts[i:i+16])
    for c, e in zip(chunks, embs):
        c["embedding"] = e
    ensure_index(dim=len(embs[0]) if embs else 3072)
    upsert_chunks(chunks)
    print(f"Indexed {len(chunks)} chunks for {pdf_id}")

if __name__ == "__main__":
    # python -m app.run_pipeline "<pdf_url>" "mok-2002-08" 2002 8
    url, pdf_id, year, month = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    process_issue(url, pdf_id, year, month)
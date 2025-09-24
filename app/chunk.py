import uuid

def chunk_pages(pages: list, max_chars=900, overlap=120):
    chunks = []
    for pg in pages:
        text = (pg["content"] or "").strip()
        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunk_text = text[start:end]
            chunk_id = f"{pg['pdf_id']}_p{pg['page_number']}_o{start}"
            chunks.append({
                "chunk_id": chunk_id,
                "pdf_id": pg["pdf_id"],
                "year": pg["year"],
                "month": pg["month"],
                "page_start": pg["page_number"],
                "page_end": pg["page_number"],
                "text": chunk_text,
                "source_blob_url": pg["source_blob_url"],
            })
            if end == len(text): break
            start = max(0, end - overlap)
    return chunks
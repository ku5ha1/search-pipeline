from statistics import mean

def normalize_ocr(doc: dict, pdf_id: str, year: int, month: int, source_blob_url: str):
    
    pages_out = []

    if "analyzeResult" in doc:
        pages = doc["analyzeResult"].get("pages", [])
        content_str = doc["analyzeResult"].get("content", "")
        for p in pages:
            confs = [w.get("confidence", 0.0) for w in p.get("words", [])]
            avg = mean(confs) if confs else 0.0
            low_ratio = (sum(c < 0.6 for c in confs) / len(confs)) if confs else 1.0
            pages_out.append({
                "pdf_id": pdf_id,
                "year": year,
                "month": month,
                "page_number": p["pageNumber"],
                "unit": p.get("unit", "unknown"),
                "width": p.get("width", 0),
                "height": p.get("height", 0),
                "angle": p.get("angle", 0),
                "content": extract_page_text(doc, p["pageNumber"]),
                "page_confidence_avg": round(avg, 3),
                "low_confidence_ratio": round(low_ratio, 3),
                "source_blob_url": source_blob_url,
                "ocr_model_id": doc["analyzeResult"].get("modelId", ""),
                "ocr_api_version": doc["analyzeResult"].get("apiVersion", ""),
            })

    # Case 2: Pre-extracted JSON (simplified)
    elif "pages" in doc:
        for p in doc["pages"]:
            page_text = p.get("content", "")
            pages_out.append({
                "pdf_id": pdf_id,
                "year": year,
                "month": month,
                "page_number": p.get("page_number", 0),
                "unit": p.get("unit", "unknown"),
                "width": p.get("width", 0),
                "height": p.get("height", 0),
                "angle": p.get("angle", 0),
                "content": page_text,
                "page_confidence_avg": None,
                "low_confidence_ratio": None,
                "source_blob_url": source_blob_url,
                "ocr_model_id": None,
                "ocr_api_version": None,
            })

    else:
        raise ValueError("Unsupported OCR JSON format")

    return pages_out


def extract_page_text(doc: dict, page_number: int) -> str:
    
    content = doc["analyzeResult"].get("content", "")
    page_idx = page_number - 1
    if page_idx >= len(doc["analyzeResult"].get("pages", [])):
        return ""
    page = doc["analyzeResult"]["pages"][page_idx]
    text_pieces = []
    for span in page.get("spans", []):
        off, ln = span.get("offset", 0), span.get("length", 0)
        text_pieces.append(content[off:off+ln])
    return "".join(text_pieces)

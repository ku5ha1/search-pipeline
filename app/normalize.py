from statistics import mean

def normalize_ocr(doc: dict, pdf_id: str, year: int, month: int, source_blob_url: str):
    pages_out = []
    for p in doc["analyzeResult"]["pages"]:
        confs = [w.get("confidence", 0.0) for w in p.get("words", [])]
        avg = mean(confs) if confs else 0.0
        low_ratio = (sum(c < 0.6 for c in confs) / len(confs)) if confs else 1.0
        pages_out.append({
            "pdf_id": pdf_id,
            "year": year,
            "month": month,
            "page_number": p["pageNumber"],
            "unit": p["unit"],
            "width": p["width"],
            "height": p["height"],
            "angle": p.get("angle", 0),
            "content": extract_page_text(doc, p["pageNumber"]),
            "page_confidence_avg": round(avg, 3),
            "low_confidence_ratio": round(low_ratio, 3),
            "source_blob_url": source_blob_url,
            "ocr_model_id": doc["analyzeResult"]["modelId"],
            "ocr_api_version": doc["analyzeResult"]["apiVersion"],
        })
    return pages_out

def extract_page_text(doc: dict, page_number: int) -> str:
    content = doc["analyzeResult"]["content"]
    for span in doc["analyzeResult"]["pages"][page_number-1]["spans"]:
        off, ln = span["offset"], span["length"]
        return content[off:off+ln]
    return ""
from statistics import mean

def normalize_ocr(doc: dict, pdf_id: str, year: int, month: int, source_blob_url: str):
    
    pages_out = []
    analyze_result = doc.get("analyzeResult", {})
    pages = analyze_result.get("pages", [])

    for p in pages:
        
        confs = [w.get("confidence", 0.0) for w in p.get("words", [])]
        avg_conf = mean(confs) if confs else 0.0
        low_conf_ratio = (sum(c < 0.6 for c in confs) / len(confs)) if confs else 1.0

        pages_out.append({
            "pdf_id": pdf_id,
            "year": year,
            "month": month,
            "page_number": p.get("pageNumber"),
            "unit": p.get("unit"),
            "width": p.get("width"),
            "height": p.get("height"),
            "angle": p.get("angle", 0),
            "content": extract_page_text(doc, p.get("pageNumber")),
            "page_confidence_avg": round(avg_conf, 3),
            "low_confidence_ratio": round(low_conf_ratio, 3),
            "source_blob_url": source_blob_url,
            "ocr_model_id": analyze_result.get("modelId"),
            "ocr_api_version": analyze_result.get("apiVersion"),
        })
    return pages_out


def extract_page_text(doc: dict, page_number: int) -> str:
    
    analyze_result = doc.get("analyzeResult", {})
    content = analyze_result.get("content", "")
    pages = analyze_result.get("pages", [])

    if not pages or page_number < 1 or page_number > len(pages):
        return ""

    spans = pages[page_number - 1].get("spans", [])
    page_text = "".join(content[span["offset"]:span["offset"] + span["length"]] for span in spans)
    return page_text

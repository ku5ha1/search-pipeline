from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.exceptions import HttpResponseError

app = FastAPI(title="Magazine Search API")


SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")

if not all([SEARCH_ENDPOINT, SEARCH_KEY, INDEX_NAME, AOAI_ENDPOINT, AOAI_KEY]):
    raise EnvironmentError("Missing required Azure or OpenAI environment variables.")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    year: int | None = None
    month: int | None = None

def embed_query(q: str) -> list[float]:
    if not q.strip():
        return []
    url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
    headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"input": q})
    resp.raise_for_status()
    data = resp.json()
    if "data" not in data or not data["data"]:
        raise ValueError("Embedding API returned empty response.")
    return data["data"][0]["embedding"]


@app.post("/search")
def search(req: SearchRequest):
    try:
        vec = embed_query(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))

    filt = []
    if req.year is not None: filt.append(f"year eq {req.year}")
    if req.month is not None: filt.append(f"month eq {req.month}")
    filt_str = " and ".join(filt) if filt else None

    vq = VectorizedQuery(vector=vec, k_nearest_neighbors=req.top_k, fields="embedding")
    results, mode = None, "semantic"
    total_count = None

    try:
        resp = sc.search(
            search_text=req.query,
            vector_queries=[vq],
            top=req.top_k,
            filter=filt_str,
            semantic_configuration_name="default",
            query_type="semantic",
            include_total_count=True
        )
        results = list(resp)
        try:
            total_count = resp.get_count()
        except Exception:
            total_count = None
    except HttpResponseError:

        mode = "vector+keyword"
        try:
            resp = sc.search(
                search_text=req.query,
                vector_queries=[vq],
                top=req.top_k,
                filter=filt_str,
                include_total_count=True
            )
            results = list(resp)
            try:
                total_count = resp.get_count()
            except Exception:
                total_count = None
        except HttpResponseError:

            mode = "vector+keyword_no_filter"
            resp = sc.search(
                search_text=req.query,
                vector_queries=[vq],
                top=req.top_k,
                include_total_count=True
            )
            results = list(resp)
            try:
                total_count = resp.get_count()
            except Exception:
                total_count = None

    out = []
    for i, r in enumerate(results):
        out.append({
            "rank": i+1,
            "score": r.get("@search.score", 0.0),
            "pdf_id": r.get("pdf_id"),
            "year": r.get("year"),
            "month": r.get("month"),
            "page": r.get("page_start"),
            "chunk_id": r.get("chunk_id"),
            "source_blob_url": r.get("source_blob_url"),
            "snippet": (r.get("text")[:250] + "…") if r.get("text") else ""
        })

    return {
        "query": req.query,
        "top_k": req.top_k,
        "filter_applied": filt_str,
        "mode": mode,
        "count": total_count,
        "results": out
    }

@app.get("/debug/index")
def debug_index():
    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
    try:
        total_docs = sc.search(search_text="*", top=0, include_total_count=True).get_count()
        facets_resp = sc.search(search_text="*", facets=["year,count:50", "month,count:12"], top=0)
        sample = []
        for r in sc.search(search_text="*", top=1):
            sample.append({
                "chunk_id": r.get("chunk_id"),
                "pdf_id": r.get("pdf_id"),
                "year": r.get("year"),
                "month": r.get("month"),
                "page_start": r.get("page_start"),
            })
            break
    except HttpResponseError as e:
        raise HTTPException(status_code=500, detail=f"Search debug failed: {e}")

    return {
        "index": INDEX_NAME,
        "total_docs": total_docs,
        "facets": getattr(facets_resp, "facets", None),
        "sample": sample
    }

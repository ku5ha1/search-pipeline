from fastapi import FastAPI, Query
from pydantic import BaseModel
import os, requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.exceptions import HttpResponseError

app = FastAPI()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")
AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    year: int | None = None
    month: int | None = None

def embed_query(q: str):
    url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
    headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"input": q})
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]

@app.post("/search")
def search(req: SearchRequest):
    vec = embed_query(req.query)
    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
    filt = []
    if req.year is not None: filt.append(f"year eq {req.year}")
    if req.month is not None: filt.append(f"month eq {req.month}")
    filt_str = " and ".join(filt) if filt else None
    vq = VectorizedQuery(vector=vec, k_nearest_neighbors=req.top_k, fields="embedding")
    mode = "semantic"
    try:
        results = sc.search(
            search_text=req.query,
            vector_queries=[vq],
            top=req.top_k,
            filter=filt_str,
            semantic_configuration_name="default",
            query_type="semantic",
            include_total_count=True
        )
    except HttpResponseError:
        try:
            mode = "vector+keyword"
            results = sc.search(
                search_text=req.query,
                vector_queries=[vq],
                top=req.top_k,
                filter=filt_str,
                include_total_count=True
            )
        except HttpResponseError:
            mode = "vector+keyword_no_filter"
            results = sc.search(
                search_text=req.query,
                vector_queries=[vq],
                top=req.top_k,
                include_total_count=True
            )
    out = []
    for i, r in enumerate(results):
        out.append({
            "rank": i+1,
            "score": r["@search.score"],
            "pdf_id": r["pdf_id"],
            "year": r["year"],
            "month": r["month"],
            "page": r["page_start"],
            "chunk_id": r["chunk_id"],
            "source_blob_url": r.get("source_blob_url"),
            "snippet": (r["text"][:250] + "…") if r.get("text") else ""
        })
    return {
        "query": req.query,
        "top_k": req.top_k,
        "filter_applied": filt_str,
        "mode": mode,
        "count": getattr(results, 'get_count', lambda: None)(),
        "results": out
    }
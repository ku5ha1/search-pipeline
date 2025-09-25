import os
import requests
from typing import List

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
if not AOAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment")
AOAI_ENDPOINT = AOAI_ENDPOINT.rstrip("/")

AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
if not AOAI_KEY:
    raise ValueError("AZURE_OPENAI_KEY not found in environment")

EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")

BATCH_SIZE = 16

def embed_texts(texts: List[str]) -> List[List[float]]:
    
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
        headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
        payload = {"input": batch}

        try:
            resp = requests.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            embeddings.extend(batch_embeddings)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Embedding request failed for batch {i}-{i+len(batch)-1}: {e}")
            raise e

    return embeddings

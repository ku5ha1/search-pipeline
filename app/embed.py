import os, requests

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")

def embed_texts(texts: list[str]) -> list[list[float]]:
    url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
    headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"input": texts})
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]
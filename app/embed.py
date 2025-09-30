import os
import time
import requests
from typing import List
from dotenv import load_dotenv

load_dotenv()

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
if not AOAI_ENDPOINT:
    raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment")
AOAI_ENDPOINT = AOAI_ENDPOINT.rstrip("/")

AOAI_KEY = os.getenv("AZURE_OPENAI_KEY")
if not AOAI_KEY:
    raise ValueError("AZURE_OPENAI_KEY not found in environment")

EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")
BATCH_SIZE = 16
MAX_RETRIES = 5
BACKOFF_FACTOR = 2  

def embed_texts(texts: List[str]) -> List[List[float]]:
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_MODEL}/embeddings?api-version=2024-06-01"
        headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
        payload = {"input": batch}

        retries = 0
        while retries <= MAX_RETRIES:
            try:
                resp = requests.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                embeddings.extend(batch_embeddings)
                break 
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429:
                    wait_time = BACKOFF_FACTOR ** retries
                    print(f"[WARN] 429 Too Many Requests. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"[ERROR] HTTP error for batch {i}-{i+len(batch)-1}: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Request failed for batch {i}-{i+len(batch)-1}: {e}")
                raise

        if retries > MAX_RETRIES:
            raise RuntimeError(f"[ERROR] Failed to embed batch {i}-{i+len(batch)-1} after {MAX_RETRIES} retries")

    return embeddings

# if __name__ == "__main__":
#     sample_texts = ["Hello world", "Azure OpenAI embeddings test"]
#     vectors = embed_texts(sample_texts)
#     print(f"Generated {len(vectors)} embeddings")

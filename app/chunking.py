import uuid

def chunk_pages(pages: list, max_chars=900, overlap=120):
    chunks = []
    for pg in pages:
        text = (pg["content"] or "").strip()
        start = 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunk_text = text[start:end]
            chunk_id = f"{pg['pdf_id']}_p{pg['page_number']}_o{start}".replace(" ", "_")
            chunks.append({
                "chunk_id": str(chunk_id),             
                "pdf_id": str(pg["pdf_id"]),           
                "year": int(pg["year"]),               
                "month": int(pg["month"]),             
                "page_start": int(pg["page_number"]),  
                "page_end": int(pg["page_number"]),    
                "text": chunk_text,
                "source_blob_url": str(pg["source_blob_url"]),  
            })
            if end == len(text): break
            start = max(0, end - overlap)
    return chunks

# import os
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
# from dotenv import load_dotenv 

# load_dotenv()

# # Environment variables
# endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
# key = os.getenv("AZURE_SEARCH_KEY")
# index_name = os.getenv("AZURE_SEARCH_INDEX")

# # Connect to the index
# search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))

# # Get all document keys
# results = search_client.search(search_text="*", select="chunk_id") 
# doc_keys = [{"chunk_id": doc["chunk_id"]} for doc in results]

# if doc_keys:
#     print(f"Deleting {len(doc_keys)} documents...")
#     result = search_client.delete_documents(documents=doc_keys)
#     print("Deleted documents:", result)
# else:
#     print("No documents found to delete.")

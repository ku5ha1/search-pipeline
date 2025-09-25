import os
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceExistsError, HttpResponseError
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchField,
    SearchFieldDataType,
    SearchableField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields
)
from azure.search.documents import SearchClient

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX", "mok-chunks")


def ensure_index(dim: int):
    sic = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))

    fields = [
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="pdf_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="year", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
        SimpleField(name="month", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
        SimpleField(name="page_start", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="page_end", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="text", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=dim,
            vector_search_profile_name="default"
        ),
        SimpleField(name="source_blob_url", type=SearchFieldDataType.String, filterable=False, sortable=False),
    ]

    vector_search = VectorSearch(
        profiles=[{"name": "default", "algorithm": "hnsw"}],
        algorithms=[{"name": "hnsw", "kind": "hnsw"}]
    )

    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="text")]
        )
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_configurations=[semantic_config]
    )

    try:
        sic.create_index(index)
        print(f"[INFO] Created new index {INDEX_NAME}")
    except Exception as e:
        if "ResourceNameAlreadyInUse" in str(e):
            print(f"[INFO] Index {INDEX_NAME} already exists — using existing index")
        else:
            raise

def upsert_chunks(docs: list[dict], batch_size: int = 1000):
    
    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))

    results = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        try:
            resp = sc.merge_or_upload_documents(documents=batch)
            results.extend(resp)
            print(f"Uploaded batch {i}-{i + len(batch) - 1}, {len(resp)} documents.")
        except HttpResponseError as e:
            print(f"[ERROR] Failed to upload batch {i}-{i + len(batch) - 1}: {e}")
            raise e

    return results

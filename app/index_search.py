import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchField, SearchFieldDataType, VectorSearch,
    VectorSearchAlgorithmConfiguration, HnswAlgorithmConfiguration, SearchableField, SemanticConfiguration, SemanticSettings, SemanticField, PrioritizedFields
)
from azure.search.documents import SearchClient

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

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
        SearchField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                    vector_search_dimensions=dim, vector_search_configuration="hnsw"),
        SimpleField(name="source_blob_url", type=SearchFieldDataType.String, filterable=False, sortable=False)
    ]
    vs = VectorSearch(algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
                      algorithm_configurations=[VectorSearchAlgorithmConfiguration(name="hnsw", kind="hnsw")])
    sem = SemanticSettings(configurations=[SemanticConfiguration(
        name="default", prioritized_fields=PrioritizedFields(content_fields=[SemanticField(field_name="text")])
    )])
    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vs, semantic_settings=sem)
    try:
        sic.create_index(index)
    except Exception:
        pass

def upsert_chunks(docs: list[dict]):
    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
    return sc.upload_documents(documents=docs)
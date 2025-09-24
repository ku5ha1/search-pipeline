import os, time
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

DOCINT_ENDPOINT = os.getenv("DOCINT_ENDPOINT")
DOCINT_KEY = os.getenv("DOCINT_KEY")

client = DocumentIntelligenceClient(DOCINT_ENDPOINT, AzureKeyCredential(DOCINT_KEY))

def ocr_pdf_url(pdf_url: str) -> dict:
    poller = client.begin_analyze_document("prebuilt-read", {"urlSource": pdf_url})
    result = poller.result()
    return result.to_dict()
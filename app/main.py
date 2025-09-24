from fastapi import FastAPI 
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "service up and running"}

key = os.getenv("key")
endpoint = os.getenv("endpoint")
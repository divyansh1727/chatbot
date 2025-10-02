from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import faiss
import numpy as np
import os
from openai import OpenAI


# ✅ Load OpenAI key
client = OpenAI(api_key="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")

# --- FastAPI setup ---
app = FastAPI()

# Allow React frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory FAISS store ---
DIM = 1536  # embedding size for text-embedding-3-small
index = faiss.IndexFlatL2(DIM)
chunks_store = []  # keep track of text chunks

# --- Models ---
class Query(BaseModel):
    query: str

class IngestRequest(BaseModel):
    url: str

# --- Helpers ---
def scrape_page(url: str):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def get_embedding_safe(text: str):
    """
    MOCK embedding for local testing.
    Returns a random vector of size 1536 instead of calling OpenAI.
    """
    return np.random.rand(1536).astype("float32").tolist()

# --- Endpoints ---
@app.post("/ingest")
def ingest(req: IngestRequest):
    global chunks_store, index
    url = req.url.strip().strip('"')
    try:
        print(f"[DEBUG] Scraping URL: {url}")
        text = scrape_page(url)
        print(f"[DEBUG] Scraped text length: {len(text)}")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text found on the page.")

        chunks = chunk_text(text)
        print(f"[DEBUG] Number of chunks: {len(chunks)}")

        for chunk in chunks:
            emb = get_embedding_safe(chunk)
            emb = np.array([emb], dtype="float32")
            index.add(emb)
            chunks_store.append(chunk)

        return {"status": "success", "chunks_stored": len(chunks)}

    except requests.RequestException as e:
        print("[ERROR] Requests error:", e)
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        print("[ERROR] Ingest failed:", e)
        raise HTTPException(status_code=500, detail=f"Ingest error: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Backend is running successfully 🚀"}
@app.post("/ask")
def ask(query: Query):
    if not chunks_store:
        return {"answer": "⚠️ No data ingested yet. Please call /ingest first."}

    q_emb = get_embedding_safe(query.query)
    q_emb = np.array([q_emb], dtype="float32")
    distances, indices = index.search(q_emb, k=3)

    retrieved = [chunks_store[i] for i in indices[0]]
    answer = " ".join(retrieved[:2])  # simple concatenation for now

    return {"answer": answer}

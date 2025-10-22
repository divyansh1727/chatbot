from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import faiss
import numpy as np
import time
from sentence_transformers import SentenceTransformer

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
DIM = 384  # dimension for all-MiniLM-L6-v2 embeddings
index = faiss.IndexFlatL2(DIM)
chunks_store = []

# --- Load local embedding model ---
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# --- Models ---
class Query(BaseModel):
    query: str

class IngestRequest(BaseModel):
    url: str

# --- Helpers ---
def scrape_page(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {e}")

    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "table", "noscript", "svg"]):
        tag.decompose()

    content = soup.find("div", {"id": "mw-content-text"})
    text = content.get_text(separator=" ", strip=True) if content else soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    if len(text) < 200:
        print("[WARN] Very short text scraped. Site might have blocked scraping.")
    return text

def chunk_text(text, chunk_size=200, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def get_embedding_safe(text: str):
    """Generate embedding vector using local model."""
    return embedding_model.encode(text).tolist()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "🚀 Local embeddings RAG backend running successfully!"}

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
        print(f"[DEBUG] Total chunks: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            emb = get_embedding_safe(chunk)
            emb = np.array([emb], dtype="float32")
            index.add(emb)
            chunks_store.append(chunk)
            print(f"[INFO] Added chunk {i+1}/{len(chunks)}")
            time.sleep(0.1)  # small delay

        return {"status": "success", "chunks_stored": len(chunks)}

    except Exception as e:
        print(f"[ERROR] Ingest error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest error: {str(e)}")

@app.post("/ask")
def ask(query: Query):
    if not chunks_store:
        return {"answer": "⚠️ No data ingested yet. Please call /ingest first."}

    try:
        q_emb = get_embedding_safe(query.query)
        q_emb = np.array([q_emb], dtype="float32")

        distances, indices = index.search(q_emb, k=3)
        retrieved = [chunks_store[i] for i in indices[0]]
        context = " ".join(retrieved)

        # Simple local "response" using context
        answer = f"Based on the ingested context: {context[:500]}..."  # return first 500 chars
        return {"answer": answer}

    except Exception as e:
        print(f"[ERROR] Ask endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Ask endpoint error: {str(e)}")

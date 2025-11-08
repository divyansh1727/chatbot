from transformers import pipeline
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import faiss
import numpy as np
import time
from sentence_transformers import SentenceTransformer

# --- Load Models ---
print("🔄 Loading models... this may take a moment.")
emotion_model = pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion")
chat_model = pipeline("text-generation", model="distilgpt2", max_length=200, temperature=0.7)


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Models loaded successfully!")

# --- FastAPI Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Memory / Store ---
DIM = 384
index = faiss.IndexFlatL2(DIM)
chunks_store = []
conversation_history = []

# --- Data Models ---
class Query(BaseModel):
    query: str

class IngestRequest(BaseModel):
    url: str

class TextIngestRequest(BaseModel):
    text: str

# --- Helper Functions ---
def scrape_page(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {e}")

    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    if len(text) < 200:
        print("[WARN] Very short text scraped — site may be JS-rendered.")
    return text


def chunk_text(text, chunk_size=200, overlap=50):
    """Splits large text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def get_embedding_safe(text: str):
    return embedding_model.encode(text).tolist()


# --- Routes ---
@app.get("/")
def root():
    return {"message": "🚀 Local embeddings RAG backend with emotion-based chatbot active!"}


@app.post("/ingest")
def ingest(req: IngestRequest):
    """Scrape and ingest a webpage."""
    global chunks_store, index
    url = req.url.strip().strip('"')
    print(f"[DEBUG] Scraping: {url}")
    text = scrape_page(url)
    chunks = chunk_text(text)
    for chunk in chunks:
        emb = np.array([get_embedding_safe(chunk)], dtype="float32")
        index.add(emb)
        chunks_store.append(chunk)
        time.sleep(0.05)
    return {"status": "success", "chunks_stored": len(chunks)}


@app.post("/ingest_text")
def ingest_text(req: TextIngestRequest):
    """Ingest custom text directly (like your CourseTeen details)."""
    global chunks_store, index
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for ingestion.")
    chunks = chunk_text(text)
    for chunk in chunks:
        emb = np.array([get_embedding_safe(chunk)], dtype="float32")
        index.add(emb)
        chunks_store.append(chunk)
    return {"status": "success", "chunks_stored": len(chunks)}


@app.post("/ingest_url")
def ingest_url(req: IngestRequest):
    """Auto-ingest data from a live website like CourseTeen."""
    global chunks_store, index
    url = req.url.strip().strip('"')
    print(f"[INFO] Fetching and embedding from: {url}")
    try:
        text = scrape_page(url)
        chunks = chunk_text(text)
        for chunk in chunks:
            emb = np.array([get_embedding_safe(chunk)], dtype="float32")
            index.add(emb)
            chunks_store.append(chunk)
        return {"status": "success", "chunks_stored": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting URL: {e}")


@app.post("/ask")
def ask(query: Query):
    """Answer questions using RAG + Emotion detection."""
    global conversation_history

    if not chunks_store:
        return {"answer": "⚠️ No data ingested yet. Please use /ingest or /ingest_text first.", "mood": "neutral"}

    # --- Retrieve most relevant context ---
    q_emb = np.array([get_embedding_safe(query.query)], dtype="float32")
    distances, indices = index.search(q_emb, k=3)
    retrieved = [chunks_store[i] for i in indices[0]]
    context = " ".join(retrieved)

    # --- Emotion detection ---
    emotion_result = emotion_model(query.query)[0]
    emotion = emotion_result["label"].lower()
    confidence = round(emotion_result["score"] * 100, 2)

    emoji_map = {
        "anger": "😠",
        "joy": "😄",
        "sadness": "😢",
        "fear": "😨",
        "love": "❤️",
        "surprise": "😲",
    }
    emoji = emoji_map.get(emotion, "🙂")

    tone_instructions = {
        "joy": "Respond in a cheerful, upbeat tone.",
        "sadness": "Respond empathetically and offer encouragement.",
        "anger": "Stay calm and respond respectfully.",
        "love": "Respond warmly and positively.",
        "fear": "Reassure the user gently.",
        "surprise": "Respond with excitement and positivity.",
    }
    tone = tone_instructions.get(emotion, "Respond helpfully and clearly.")

    # --- Build prompt ---
    prompt = (
        f"Context: {context[:700]}\n"
        f"{tone}\n"
        f"Conversation history:\n{conversation_history[-3:]}\n"
        f"User: {query.query}\nAssistant:"
    )

    result = chat_model(prompt, do_sample=True, temperature=0.8, max_new_tokens=100)
    answer = result[0]["generated_text"].split("Assistant:")[-1].strip()


   

    conversation_history.append(f"User: {query.query}")
    conversation_history.append(f"Assistant: {answer}")

    return {
        "answer": f"{emoji} {answer}",
        "mood": emotion,
        "confidence": confidence,
    }

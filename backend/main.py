from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import faiss
import numpy as np

# -------------------------------
# 🔹 MODEL LOADING
# -------------------------------
print("🔄 Loading models... please wait.")
emotion_model = pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion")
chat_model = pipeline("text2text-generation", model="google/flan-t5-base")  # ✅ safe, smart, light
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Models loaded successfully!")

# -------------------------------
# 🔹 FASTAPI SETUP
# -------------------------------
app = FastAPI(title="CourseTeen Chatbot Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# 🔹 VECTOR STORE (FAISS)
# -------------------------------
DIM = 384
index = faiss.IndexFlatL2(DIM)
chunks_store = []

# -------------------------------
# 🔹 DATA MODELS
# -------------------------------
class Query(BaseModel):
    query: str

class IngestRequest(BaseModel):
    url: str

class TextIngestRequest(BaseModel):
    text: str

# -------------------------------
# 🔹 HELPERS
# -------------------------------
def chunk_text(text, chunk_size=200, overlap=50):
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def get_embedding(text: str):
    """Get vector embedding."""
    return embedding_model.encode(text).tolist()

def scrape_page_playwright(url: str) -> str:
    """Scrape JS-rendered page content."""
    print(f"[INFO] Navigating to {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page.goto(url, timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=40000)
        except Exception:
            print("[WARN] Network idle timeout; continuing anyway.")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())

def ingest_text_internal(text: str):
    """Embed and store text in FAISS."""
    global index, chunks_store
    chunks = chunk_text(text)
    for chunk in chunks:
        emb = np.array([get_embedding(chunk)], dtype="float32")
        index.add(emb)
        chunks_store.append(chunk)
    print(f"✅ Stored {len(chunks)} chunks.")

# -------------------------------
# 🔹 ROUTES
# -------------------------------
@app.get("/")
def root():
    return {"message": "🚀 CourseTeen RAG + Emotion Chatbot running!"}

@app.post("/ingest_url")
def ingest_url(req: IngestRequest):
    """Scrape and embed content from a site."""
    url = req.url.strip()
    try:
        text = scrape_page_playwright(url)
        if len(text) < 100:
            raise HTTPException(status_code=500, detail="Empty or blocked page.")
        ingest_text_internal(text)
        return {"status": "success", "chunks_stored": len(chunks_store)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting URL: {e}")

@app.post("/ingest_text")
def ingest_text(req: TextIngestRequest):
    """Manually ingest text."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    ingest_text_internal(text)
    return {"status": "success", "chunks_stored": len(chunks_store)}

@app.post("/ask")
def ask(query: Query):
    """Answer using context + emotion awareness."""
    if not chunks_store:
        return {"answer": "⚠️ Please ingest some text first.", "mood": "neutral"}

    user_input = query.query.strip()
    q_emb = np.array([get_embedding(user_input)], dtype="float32")
    distances, indices = index.search(q_emb, k=3)
    context = " ".join(chunks_store[i] for i in indices[0])

    # Detect emotion
    emotion_result = emotion_model(user_input)[0]
    emotion = emotion_result["label"].lower()
    confidence = round(emotion_result["score"] * 100, 2)

    emoji_map = {
        "anger": "😠", "joy": "😄", "sadness": "😢",
        "fear": "😨", "love": "❤️", "surprise": "😲"
    }
    emoji = emoji_map.get(emotion, "🙂")

    # Build smart prompt for Flan-T5
    prompt = (
        f"The user is feeling {emotion}. Be empathetic.\n\n"
        f"Use the context below to answer clearly:\n"
        f"Context: {context[:700]}\n\n"
        f"User: {user_input}\n"
        f"Assistant:"
    )

    try:
        result = chat_model(prompt, max_new_tokens=200, temperature=0.6, top_p=0.9)
        answer = result[0]["generated_text"].split("Assistant:")[-1].strip()
        return {"answer": f"{emoji} {answer}", "mood": emotion, "confidence": confidence}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {e}")

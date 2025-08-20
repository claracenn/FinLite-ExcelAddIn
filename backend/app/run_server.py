from pydoc import text
import sys, os
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent

print("===== DIST CONTENTS =====")
for p in sorted(BASE.iterdir()):
    print("  ", p.name)
print("=========================")

sys.path.insert(0, str(BASE / "src"))

import traceback
import re
import json
import pandas as pd
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from collections import deque
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from faster_whisper import WhisperModel
import tempfile
import shutil

import uvicorn

from table_main    import rag_pipeline
from llm_embedding import build_index
from table_linearizer import linearize
from llm_generating import generate_answer
from save_jsonl import LOG_PATH, save_interaction

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)

# Initialize Whisper model for speech recognition
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        # Use "base" model for good balance of speed and accuracy
        # You can use "tiny", "base", "small", "medium", "large" based on your needs
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    executor.shutdown(wait=True)

app = FastAPI(title="ExcelRAG Service", lifespan=lifespan)

# Add CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHUNKS: List[str] = []

class ChatRequest(BaseModel):
    prompt: str
    snippets: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str

class SpeechResponse(BaseModel):
    text: str

@app.post("/speech-to-text", response_model=SpeechResponse)
async def speech_to_text(audio_file: UploadFile = File(...)):
    """
    Convert speech audio file to text using faster-whisper
    """
    try:
        # Read the uploaded audio file
        audio_data = await audio_file.read()
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Get the Whisper model
            model = get_whisper_model()
            
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def transcribe_audio():
                segments, info = model.transcribe(temp_file_path, beam_size=5)
                # Combine all segments into a single text
                text = ""
                for segment in segments:
                    text += segment.text
                return text.strip()
            
            text = await loop.run_in_executor(executor, transcribe_audio)
            
            if not text:
                raise HTTPException(status_code=400, detail="No speech detected in audio")
            
            return SpeechResponse(text=text)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.post("/initialize")
async def initialize(req: Request):
    body = await req.json()
    excel_path = body["path"]

    sheets = pd.read_excel(excel_path, sheet_name=None, engine="openpyxl")
    chunks = []
    for sheet_name, df in sheets.items():
        rows = linearize(df)
        chunks.extend(f"[{sheet_name}] {row}" for row in rows)
        
    build_index(chunks)
    global CHUNKS
    CHUNKS = chunks
    return {"status": "index rebuilt", "snippets": len(chunks)}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        if req.snippets:
            full_prompt = (
                "You are a helpful assistant. Use only the provided table data to answer the question.\n\n"
                + "\n".join(req.snippets)
                + f"\n\nQuestion: {req.prompt}\nAnswer:"
            )
            # Run the blocking LLM generation in a thread pool
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(executor, generate_answer, full_prompt)
        else:
            # Run the entire RAG pipeline in a thread pool
            loop = asyncio.get_event_loop()
            selected_chunks, raw = await loop.run_in_executor(executor, rag_pipeline, req.prompt)
        
        answer = trim_to_first_answer(raw)
        
        # Run the save operation in a thread pool as well (in case it's also blocking)
        if req.snippets:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, save_interaction, req.prompt, req.snippets, answer)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, save_interaction, req.prompt, selected_chunks, answer)
            
        return ChatResponse(response=answer)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/history")
def get_history(limit: int = 5) -> List[Dict]:
    if not LOG_PATH.exists():
        return []  # no history yet
    buf = deque(maxlen=limit)
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                rec = json.loads(line)
                rec["_id"] = i
                buf.append(rec)
            except Exception:
                continue
    items = list(buf)
    items.reverse()
    return [
        {
            "id": it.get("_id"),
            "title": _title_from_prompt(it.get("prompt", "")),
            "prompt": it.get("prompt", ""),
            "timestamp": it.get("timestamp", ""),
        }
        for it in items
    ]

@app.get("/history/{item_id}")
def get_history_item(item_id: int) -> Dict:
    if not LOG_PATH.exists():
        raise HTTPException(status_code=404, detail="No history")
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == item_id:
                try:
                    rec = json.loads(line)
                    rec["_id"] = i
                    return rec
                except Exception:
                    break
    raise HTTPException(status_code=404, detail="Not found")


def _title_from_prompt(p: str, limit: int = 50) -> str:
    p = (p or "").strip().replace("\n", " ")
    return (p[:limit] + "…") if len(p) > limit else (p or "New Chat")

def trim_to_first_answer(text: str) -> str:
    parts = re.split(r"\n?(?:Question:|Selected range)", text, maxsplit=1)
    return parts[0].strip()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

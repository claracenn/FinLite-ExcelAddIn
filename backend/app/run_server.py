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

executor = ThreadPoolExecutor(max_workers=2)

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    load_formula_templates()
    yield
    # Shutdown
    executor.shutdown(wait=True)

app = FastAPI(title="ExcelRAG Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHUNKS: List[str] = []
FORMULA_TEMPLATES: Dict[str, Dict[str, str]] = {}

def load_formula_templates():
    """Load predefined financial formulas from JSON file"""
    global FORMULA_TEMPLATES
    try:
        formula_file_path = BASE / "fin_formula.json"
        if formula_file_path.exists():
            with open(formula_file_path, 'r', encoding='utf-8') as f:
                FORMULA_TEMPLATES = json.load(f)
            print(f"Loaded {len(FORMULA_TEMPLATES)} formula templates")
        else:
            print("Formula templates file not found, using empty templates")
            FORMULA_TEMPLATES = {}
    except Exception as e:
        print(f"Error loading formula templates: {e}")
        FORMULA_TEMPLATES = {}

def find_matching_template(prompt: str) -> Optional[str]:
    """Find a matching formula template key based on user prompt"""
    prompt_upper = prompt.upper().strip()
    
    # Direct key match (case-insensitive)
    for key in FORMULA_TEMPLATES.keys():
        if key.upper() == prompt_upper:
            return key
    
    # Check if prompt contains any template key
    for key in FORMULA_TEMPLATES.keys():
        if key.upper() in prompt_upper or prompt_upper in key.upper():
            return key
    
    # Check for common formula variations
    formula_mappings = {
        "NET PRESENT VALUE": "NPV",
        "INTERNAL RATE OF RETURN": "IRR",
        "RETURN ON EQUITY": "ROE", 
        "RETURN ON ASSETS": "ROA",
        "COMPOUND ANNUAL GROWTH RATE": "CAGR",
        "RETURN ON INVESTMENT": "ROI",
        "WEIGHTED AVERAGE COST OF CAPITAL": "WACC",
        "EARNINGS BEFORE INTEREST TAXES DEPRECIATION AMORTIZATION": "EBITDA_Margin",
        "CURRENT RATIO": "Current_Ratio",
        "DEBT TO EQUITY": "Debt_to_Equity",
        "DIVIDEND YIELD": "Dividend_Yield"
    }
    
    for phrase, key in formula_mappings.items():
        if phrase in prompt_upper:
            return key
    
    return None

class ChatRequest(BaseModel):
    prompt: str
    snippets: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str

class SpeechResponse(BaseModel):
    text: str

class FormulaRequest(BaseModel):
    prompt: str
    user_selection: Optional[str] = ""
    active_cell: Optional[str] = ""
    occupied_ranges: Optional[List[str]] = []

class FormulaResponse(BaseModel):
    explanation: str
    formula: str

class FormulaTemplateResponse(BaseModel):
    name: str
    formula: str
    description: str

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
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.post("/formula-helper", response_model=FormulaResponse)
async def formula_helper(req: FormulaRequest):
    """
    Provide formula explanations based on user request.
    First checks for predefined templates, then falls back to LLM generation.
    """
    try:
        # First, check if the prompt matches any predefined template
        template_key = find_matching_template(req.prompt)
        
        if template_key and template_key in FORMULA_TEMPLATES:
            # Return predefined template
            template_data = FORMULA_TEMPLATES[template_key]
            formula = template_data["formula"]
            description = template_data["description"]
            
            return FormulaResponse(
                explanation=description,
                formula=formula
            )
        
        formula_prompt = f"""You are an Excel formula expert. Please answer the question: {req.prompt}. 
            Provide concisely:
            1. Brief explanation of the suggested formula (1-2 sentences)
            2. Excel formula syntax
            """
        
        loop = asyncio.get_event_loop()
        raw_response = await loop.run_in_executor(executor, generate_answer, formula_prompt)
        
        # Return the raw response directly in explanation field
        return FormulaResponse(
            explanation=raw_response.strip(),
            formula="See explanation above"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating formula explanation: {str(e)}")

@app.get("/formula-template/{name}", response_model=FormulaTemplateResponse)
async def get_formula_template(name: str):
    """
    Get a predefined financial formula template by name
    """
    try:
        # Check if the template exists (case-insensitive)
        template_key = None
        for key in FORMULA_TEMPLATES.keys():
            if key.upper() == name.upper():
                template_key = key
                break
        
        if template_key is None:
            raise HTTPException(status_code=404, detail=f"Formula template '{name}' not found")
        
        template_data = FORMULA_TEMPLATES[template_key]
        
        return FormulaTemplateResponse(
            name=template_key,
            formula=template_data["formula"],
            description=template_data["description"]
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving formula template: {str(e)}")

@app.get("/formula-templates")
async def list_formula_templates():
    """
    Get a list of all available formula templates
    """
    try:
        templates = []
        for name, template_data in FORMULA_TEMPLATES.items():
            templates.append({
                "name": name,
                "formula": template_data["formula"]
            })
        return {"templates": templates, "count": len(templates)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error listing formula templates: {str(e)}")

@app.post("/initialize")
async def initialize(req: Request):
    """
    Initialize the service with the provided Excel file.
    """
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
    """
    Chat endpoint for user queries
    """
    try:
        if req.snippets:
            full_prompt = (
                "You are a helpful assistant. Use only the provided table data to answer the question.\n\n"
                + "\n".join(req.snippets)
                + f"\n\nQuestion: {req.prompt}\nAnswer:"
            )
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(executor, generate_answer, full_prompt)
        else:
            loop = asyncio.get_event_loop()
            selected_chunks, raw = await loop.run_in_executor(executor, rag_pipeline, req.prompt)
        
        answer = trim_to_first_answer(raw)
        
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

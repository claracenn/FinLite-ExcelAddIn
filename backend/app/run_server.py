from pydoc import text
import sys, os
import logging
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).parent

print("===== DIST CONTENTS =====")
for p in sorted(BASE.iterdir()):
    print("  ", p.name)
print("=========================")

src_top = BASE / "src"
src_internal = BASE / "_internal" / "src"
for p in (src_top, src_internal):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import traceback
import re
import json
import pandas as pd
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
from collections import deque
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from faster_whisper import WhisperModel
import tempfile
import shutil
from functools import partial

import uvicorn

from table_main    import rag_pipeline, set_current_chunks, load_excel_data, get_current_chunks
from llm_embedding import build_index
from table_linearizer import linearize
from llm_generating import generate_answer
from save_jsonl import LOG_PATH, save_interaction

executor = ThreadPoolExecutor(max_workers=2)
def _log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "FinLite" / "logs"
    return Path.cwd() / "logs"

_LOG_DIR = _log_dir()
_LOG_DIR.mkdir(parents=True, exist_ok=True)
server_logger = logging.getLogger("server")
if not server_logger.handlers:
    server_logger.setLevel(logging.INFO)
    fh = logging.FileHandler(str(_LOG_DIR / "server-errors.log"), encoding="utf-8")
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    server_logger.addHandler(fh)

PID_FILE = _LOG_DIR / "backend.pid"

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    load_formula_templates()
    print("Server started. Waiting for Excel file to be loaded...")
    
    yield
    # Shutdown
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass
    executor.shutdown(wait=True)

app = FastAPI(title="ExcelRAG Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    server_logger.error("Unhandled exception: %s\n%s", exc, tb)
    payload = {"detail": str(exc)}
    if os.environ.get("FINLITE_DEBUG") == "1":
        payload["traceback"] = tb
    return JSONResponse(status_code=500, content=payload)

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
    detailed: Optional[bool] = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

class SpeechResponse(BaseModel):
    text: str

class FormulaRequest(BaseModel):
    prompt: str
    user_selection: Optional[str] = ""
    active_cell: Optional[str] = ""
    occupied_ranges: Optional[List[str]] = []
    session_id: Optional[str] = ""

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
        audio_data = await audio_file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            model = get_whisper_model()
            
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
        template_key = find_matching_template(req.prompt)
        
        if template_key and template_key in FORMULA_TEMPLATES:
            template_data = FORMULA_TEMPLATES[template_key]
            formula = template_data["formula"]
            description = template_data["description"]
            
            final_response = f"**Formula Explanation:**\n{description}\n\n**Formula:**\n`{formula}`"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                partial(
                    save_interaction,
                    req.prompt,
                    [],
                    final_response,
                    session_id=req.session_id or "",
                    mode="formula",
                ),
            )
            
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
        
        await loop.run_in_executor(
            executor,
            partial(
                save_interaction,
                req.prompt,
                [],
                raw_response.strip(),
                session_id=req.session_id or "",
                mode="formula",
            ),
        )

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
    try:
        body = await req.json()
        excel_path = body.get("path")
        if not excel_path or not Path(excel_path).exists():
            raise HTTPException(status_code=400, detail=f"Excel file not found: {excel_path}")

        # Load Excel data
        chunks = load_excel_data(excel_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No data rows found in the Excel file.")

        build_index(chunks)
        set_current_chunks(chunks)

        global CHUNKS
        CHUNKS = chunks
        
        return {"status": "index rebuilt", "snippets": len(chunks)}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Initialize failed: {e}")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Chat endpoint for user queries
    """
    try:
        if req.snippets:
            loop = asyncio.get_event_loop()
            selected_chunks, _ = await loop.run_in_executor(executor, rag_pipeline, req.prompt, req.detailed)
            
            combined_snippets = req.snippets.copy()
            for chunk in selected_chunks:
                if chunk not in combined_snippets:
                    combined_snippets.append(chunk)
            
            full_prompt = (
                "You are a helpful assistant. Use the provided table data to answer the question.\n\n"
                + "\n".join(combined_snippets)
                + f"\n\nQuestion: {req.prompt}\nAnswer:"
            )
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(executor, generate_answer, full_prompt, req.detailed)
            answer = trim_to_first_answer(raw)
            used_snippets = combined_snippets
        
        else:
            loop = asyncio.get_event_loop()
            selected_chunks, raw = await loop.run_in_executor(executor, rag_pipeline, req.prompt, req.detailed)
            
            if not selected_chunks and "No workbook data available" in raw:
                raise HTTPException(status_code=400, detail="No workbook has been initialized. Please re-open the Excel file.")
            
            if selected_chunks:
                answer = trim_to_first_answer(raw)
                used_snippets = selected_chunks
            else:
                answer = raw
                used_snippets = []
        
        original_prompt = extract_original_prompt(req.prompt)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            partial(
                save_interaction,
                original_prompt,
                used_snippets,
                answer,
                session_id=req.session_id,
                mode="chat",
            ),
        )
            
        return ChatResponse(response=answer)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/history")
def get_history(limit: int = 5) -> List[Dict]:
    if not LOG_PATH.exists():
        return []
    valid_records = []
    
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                rec = json.loads(line)
                if rec.get("prompt", "").strip():
                    rec["_id"] = i
                    valid_records.append(rec)
            except Exception:
                continue
    
    recent_records = valid_records[-limit:] if len(valid_records) > limit else valid_records
    recent_records.reverse()
    
    return [
        {
            "id": it.get("_id"),
            "title": _title_from_prompt(it.get("prompt", "")),
            "prompt": it.get("prompt", ""),
            "timestamp": it.get("timestamp", ""),
            "session_id": it.get("session_id", ""),
            "mode": it.get("mode", "chat"),
        }
        for it in recent_records
    ]


def _title_from_prompt(p: str, limit: int = 50) -> str:
    p = (p or "").strip().replace("\n", " ")
    return (p[:limit] + "…") if len(p) > limit else (p or "New Chat")

def trim_to_first_answer(text: str) -> str:
    parts = re.split(r"\n?(?:Question:|Selected range)", text, maxsplit=1)
    return parts[0].strip()

def extract_original_prompt(prompt: str) -> str:
    """Extract the original user prompt by removing system directives"""
    if not prompt:
        return prompt
    
    cleaned = re.sub(r'^\s*please\s+answer\s+(?:concisely|detailedly)\s*:\s*', '', prompt, flags=re.IGNORECASE)
    return cleaned.strip()

def _group_records_by_session(records: List[Dict]) -> Dict[str, List[Tuple[int, Dict]]]:
    grouped: Dict[str, List[Tuple[int, Dict]]] = {}
    for idx, rec in records:
        sid = str(rec.get("session_id") or "")
        if not sid:
            continue
        grouped.setdefault(sid, []).append((idx, rec))
    return grouped

@app.get("/history/grouped")
def get_history_grouped(limit: int = 10) -> List[Dict]:
    """Return grouped conversations by session_id (newest first).

    Each item contains: session_id, turns, first_prompt, last_timestamp, ids
    """
    if not LOG_PATH.exists():
        return []
    records: List[Tuple[int, Dict]] = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                rec = json.loads(line)
                if (rec.get("prompt", "") or rec.get("response", "")) and rec.get("session_id"):
                    records.append((i, rec))
            except Exception:
                continue
    if not records:
        return []
    grouped = _group_records_by_session(records)
    items = []
    for sid, pairs in grouped.items():
        pairs_sorted = sorted(pairs, key=lambda x: x[0])
        first = pairs_sorted[0][1]
        last = pairs_sorted[-1][1]
        items.append({
            "session_id": sid,
            "turns": len(pairs_sorted),
            "first_prompt": first.get("prompt", ""),
            "last_timestamp": last.get("timestamp", ""),
            "ids": [i for i, _ in pairs_sorted],
        })

    def _sort_key(it):
        ts = it.get("last_timestamp") or ""
        return (ts, max(it.get("ids") or [-1]))
    items.sort(key=_sort_key, reverse=True)
    return items[:limit]

@app.get("/history/unified")
def get_history_unified(limit: int = 10) -> List[Dict]:
        """Return grouped sessions with a stable shape.

        Shape: [{
            "session_id": str,
            "turns": int,
            "first_prompt": str,
            "last_timestamp": str,
            "ids": [int]
        }]
        """
        return get_history_grouped(limit)

@app.get("/history/session/{session_id}")
def get_history_session(session_id: str) -> Dict:
    """Return full conversation for a session id."""
    if not LOG_PATH.exists():
        raise HTTPException(status_code=404, detail="No history")
    records: List[Tuple[int, Dict]] = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                rec = json.loads(line)
                sid = str(rec.get("session_id") or f"line-{i}")
                if sid == session_id:
                    rec["_id"] = i
                    records.append((i, rec))
            except Exception:
                continue
    if not records:
        raise HTTPException(status_code=404, detail="Session not found")
    records.sort(key=lambda x: x[0])
    return {
        "session_id": session_id,
        "title": _title_from_prompt(records[0][1].get("prompt", "")),
        "turns": len(records),
        "items": [
            {
                "id": i,
                "prompt": rec.get("prompt", ""),
                "response": rec.get("response", ""),
                "timestamp": rec.get("timestamp", ""),
            }
            for i, rec in records
        ]
    }

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

@app.post("/history/open")
async def post_history_open(req: Request) -> Dict:
    """Open a session or single record via one endpoint.

    Body: { "session_id": str } OR { "id": int }
    Returns: full session if possible; otherwise single record.
    """
    body = await req.json()
    sid = str(body.get("session_id") or "").strip()
    if sid:
        return get_history_session(sid)

    if "id" in body:
        try:
            target_id = int(body["id"])
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid id")

        if not LOG_PATH.exists():
            raise HTTPException(status_code=404, detail="No history")
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == target_id:
                    try:
                        rec = json.loads(line)
                        rec["_id"] = i
                        rec_sid = str(rec.get("session_id") or "").strip()
                        if rec_sid:
                            return get_history_session(rec_sid)
                        return rec
                    except Exception:
                        break
        raise HTTPException(status_code=404, detail="Not found")

    raise HTTPException(status_code=400, detail="session_id or id required")

@app.get("/status")
def get_status():
    """Get current service status including loaded data info"""
    from table_main import get_current_chunks
    current_chunks = get_current_chunks()
    
    return {
        "status": "running",
        "chunks_loaded": len(current_chunks),
        "formula_templates": len(FORMULA_TEMPLATES),
    "has_index": len(current_chunks) > 0,
        "sample_chunks": current_chunks[:3] if current_chunks else []
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

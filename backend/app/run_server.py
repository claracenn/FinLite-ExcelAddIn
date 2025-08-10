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
from typing import Dict, List, Optional
from collections import deque
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

import uvicorn

from table_main    import rag_pipeline
from llm_embedding import build_index
from table_linearizer import linearize
from llm_generating import generate_answer
from save_jsonl import LOG_PATH, save_interaction

app = FastAPI(title="ExcelRAG Service")

CHUNKS: List[str] = []

class ChatRequest(BaseModel):
    prompt: str
    snippets: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str

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
            raw = generate_answer(full_prompt)
        else:
            selected_chunks, raw = rag_pipeline(req.prompt)
        answer = trim_to_first_answer(raw)
        save_interaction(req.prompt, req.snippets or selected_chunks, answer)
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

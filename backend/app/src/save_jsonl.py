import sys, json
from pathlib import Path
from request_serializer import serialize_request
import json as _json
from datetime import datetime

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = _json.loads((ROOT / "config.json").read_text())
LOG_PATH = Path(cfg["LOG_JSONL"])
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_interaction(prompt: str, snippets: list[str], response: str):
    """Save interaction to log file with short-term deduplication check"""
    record = serialize_request(prompt, snippets, response)
    
    current_time = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
    
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Check only the last 2-3 entries for very recent duplicates
                for line in lines[-3:]:
                    try:
                        existing = json.loads(line.strip())
                        if (existing.get("prompt", "").strip() == prompt.strip() and 
                            existing.get("response", "").strip() == response.strip()):
                            existing_time = datetime.fromisoformat(existing["timestamp"].replace('Z', '+00:00'))
                            time_diff = abs((current_time - existing_time).total_seconds())
                            if time_diff < 3: 
                                return
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            pass 

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

import os
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

def _default_log_dir() -> Path:
    env = os.getenv("FINLITE_LOG_DIR")
    if env:
        p = Path(os.path.expandvars(env)).expanduser()
    else:
        base = os.getenv("LOCALAPPDATA") or str(Path.home())
        p = Path(base) / "FinLite" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

raw = cfg.get("LOG_JSONL", "requests.jsonl")
raw = os.path.expandvars(raw)
candidate = Path(raw).expanduser()

if candidate.is_absolute():
    LOG_PATH = candidate
else:
    LOG_PATH = _default_log_dir() / (candidate.name or "requests.jsonl")

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_interaction(
    prompt: str,
    snippets: list[str],
    response: str,
    *,
    session_id: str | None = None,
    mode: str = "chat",
    meta: dict | None = None,
):
    """Save interaction to log file with short-term deduplication check."""
    if not session_id:
        return
        
    record = serialize_request(prompt, snippets, response, session_id=session_id, mode=mode, meta=meta)

    try:
        current_time = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
    except Exception:
        current_time = datetime.utcnow()

    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    try:
                        existing = json.loads(line.strip())
                        if (
                            existing.get("prompt", "").strip() == prompt.strip()
                            and existing.get("response", "").strip() == response.strip()
                            and (existing.get("session_id", "") == (session_id or ""))
                            and (existing.get("mode", "chat") == (mode or "chat"))
                        ):
                            existing_time_raw = existing.get("timestamp", "")
                            existing_time = datetime.fromisoformat(str(existing_time_raw).replace('Z', '+00:00'))
                            if abs((current_time - existing_time).total_seconds()) < 5:
                                return
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            pass

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

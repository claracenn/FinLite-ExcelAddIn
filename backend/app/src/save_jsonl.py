import sys, json
from pathlib import Path
from request_serializer import serialize_request
import json as _json

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = _json.loads((ROOT / "config.json").read_text())
LOG_PATH = Path(cfg["LOG_JSONL"])
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_interaction(prompt: str, snippets: list[str], response: str):
    record = serialize_request(prompt, snippets, response)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

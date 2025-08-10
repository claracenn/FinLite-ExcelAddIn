from pathlib import Path
import json
from llama_cpp import Llama
import sys

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = json.loads((ROOT / "config.json").read_text())
MODEL_PATH = str((ROOT / cfg["MODEL_PATH"]))
LLM_PARAMS = cfg["LLM_PARAMS"]

_llm = Llama(model_path=MODEL_PATH, **LLM_PARAMS)


def generate_answer(prompt: str) -> str:
    resp = _llm(
        prompt,
        max_tokens=LLM_PARAMS["max_tokens"],
        stop=LLM_PARAMS["stop"]
    )
    return resp["choices"][0]["text"].strip()

from pathlib import Path
import json
from llama_cpp import Llama
import sys
import threading

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = json.loads((ROOT / "config.json").read_text())
MODEL_PATH = str((ROOT / cfg["MODEL_PATH"]))
LLM_PARAMS = cfg["LLM_PARAMS"]
LLM_PARAMS_DETAILED = cfg.get("LLM_PARAMS_DETAILED", LLM_PARAMS)

_llm = Llama(model_path=MODEL_PATH, **{k: v for k, v in LLM_PARAMS.items() if k != "max_tokens"})
_llm_lock = threading.Lock()


def generate_answer(prompt: str, detailed: bool = False) -> str:
    params = LLM_PARAMS_DETAILED if detailed else LLM_PARAMS
    
    with _llm_lock:
        resp = _llm(
            prompt,
            max_tokens=params.get("max_tokens"),
            stop=params.get("stop")
        )
    return resp["choices"][0]["text"].strip()

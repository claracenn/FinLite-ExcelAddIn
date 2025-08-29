import sys, json, os
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = json.loads((ROOT / "config.json").read_text())

EMBEDDING_MODEL = cfg["EMBEDDING_MODEL"]
INDEX_PATH = cfg["INDEX_PATH"]

_encoder = SentenceTransformer(str(ROOT / EMBEDDING_MODEL))
_index = None

def _user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "FinLite"
    # Fallback
    return Path.home() / "AppData" / "Local" / "FinLite"

def _resolved_index_path() -> Path:
    p = Path(INDEX_PATH)
    if p.is_absolute():
        return p
    # Use user-writable dir when frozen; else keep alongside project root
    if getattr(sys, "frozen", False):
        return _user_data_dir() / p.name
    return (ROOT / p)

def build_index(chunks: list[str]) -> None:
    embs = _encoder.encode(chunks, convert_to_numpy=True)
    dim = embs.shape[1]
    idx = faiss.IndexFlatL2(dim)
    idx.add(embs)
    out_path = _resolved_index_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(idx, str(out_path))

def load_index():
    global _index
    if _index is None:
        try:
            ip = _resolved_index_path()
            if ip.exists():
                _index = faiss.read_index(str(ip))
            else:
                return None
        except Exception as e:
            print(f"Warning: Failed to load index from {_resolved_index_path()}: {e}")
            return None
    return _index

def encode_query(query: str) -> np.ndarray:
    return _encoder.encode([query], convert_to_numpy=True)

def search_index(q_emb: np.ndarray, k: int) -> list[int]:
    idx = load_index()
    if idx is None:
        return []
    _, I = idx.search(q_emb, k)
    return I[0].tolist()

def encode_texts(texts: list[str]) -> np.ndarray:
    """Batch-encode a list of texts and return a 2D numpy array (n, d)."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    return _encoder.encode(texts, convert_to_numpy=True)

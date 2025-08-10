import sys, json
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

def build_index(chunks: list[str]) -> None:
    embs = _encoder.encode(chunks, convert_to_numpy=True)
    dim = embs.shape[1]
    idx = faiss.IndexFlatL2(dim)
    idx.add(embs)
    faiss.write_index(idx, INDEX_PATH)

def load_index():
    global _index
    if _index is None:
        _index = faiss.read_index(INDEX_PATH)
    return _index

def encode_query(query: str) -> np.ndarray:
    return _encoder.encode([query], convert_to_numpy=True)

def search_index(q_emb: np.ndarray, k: int) -> list[int]:
    idx = load_index()
    _, I = idx.search(q_emb, k)
    return I[0].tolist()

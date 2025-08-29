import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import List, Tuple
import numpy as np

try:
    from llm_embedding import encode_query, encode_texts, load_index, search_index
except Exception:
    encode_query = None  # type: ignore
    encode_texts = None  # type: ignore
    load_index = None  # type: ignore
    search_index = None  # type: ignore
from pathlib import Path
import json
import sys

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

try:
    _cfg = json.loads((ROOT / "config.json").read_text())
    _r = _cfg.get("RETRIEVAL", {})
    DEFAULT_BM25_TOP_MULT = _r.get("BM25_TOP_MULT", 5)
    DEFAULT_W_BM25 = _r.get("WEIGHT_BM25", 0.5)
    DEFAULT_W_EMBED = _r.get("WEIGHT_EMBED", 0.5)
except Exception:
    DEFAULT_BM25_TOP_MULT = 5
    DEFAULT_W_BM25 = 0.5
    DEFAULT_W_EMBED = 0.5


try:
    import regex as _uregex  # type: ignore
    _TOKEN_SPLIT = ("uregex", _uregex.compile(r"[^\p{L}\p{N}_]+"))
except Exception:
    _TOKEN_SPLIT = ("re", re.compile(r"[^\w]+", re.UNICODE))

try:
    from stopwordsiso import stopwords as _sw
    _STOPWORDS = set(_sw("en"))
except Exception:
    _STOPWORDS = set(
        [
            "the",
            "a",
            "an",
            "is",
            "are",
            "to",
            "of",
            "and",
            "in",
            "on",
            "for",
            "by",
            "with",
            "at",
            "from",
            "as",
            "it",
            "this",
            "that",
            "be",
            "or",
        ]
    )

try:
    from snowballstemmer import stemmer as _snow_stemmer
    _STEMMER = _snow_stemmer("english")
    def _maybe_stem(tok: str) -> str:
        try:
            return _STEMMER.stemWord(tok)
        except Exception:
            return tok
except Exception:
    def _maybe_stem(tok: str) -> str:
        return tok


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = _normalize_text(text).lower()
    splitter = _TOKEN_SPLIT[1]
    toks = [t for t in splitter.split(text) if t]
    toks = [t for t in toks if t not in _STOPWORDS and not t.isnumeric()]
    toks = [_maybe_stem(t) for t in toks]
    return toks


class BM25:
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_tokens: List[List[str]] = [_tokenize(doc) for doc in corpus]
        self.doc_freq: defaultdict[str, int] = defaultdict(int)
        self.doc_len: List[int] = [len(toks) for toks in self.corpus_tokens]
        self.N = len(corpus)
        for toks in self.corpus_tokens:
            for term in set(toks):
                self.doc_freq[term] += 1
        self.avgdl = (sum(self.doc_len) / self.N) if self.N > 0 else 0.0

        self.idf: dict[str, float] = {}
        for term, df in self.doc_freq.items():
            self.idf[term] = math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    def score(self, query: str) -> List[float]:
        q_toks = _tokenize(query)
        if not q_toks or self.N == 0:
            return [0.0] * self.N
        scores = [0.0] * self.N
        q_counts = Counter(q_toks)
        for i, doc_toks in enumerate(self.corpus_tokens):
            if not doc_toks:
                continue
            freq = Counter(doc_toks)
            dl = self.doc_len[i]
            denom = self.k1 * (1 - self.b + self.b * dl / (self.avgdl + 1e-9))
            s = 0.0
            for t, qtf in q_counts.items():
                if t not in freq:
                    continue
                f = freq[t]
                idf = self.idf.get(t, 0.0)
                s += idf * (f * (self.k1 + 1)) / (f + denom)
            scores[i] = s
        return scores


def _normalize(xs: List[float]) -> List[float]:
    if not xs:
        return []
    mn = min(xs)
    mx = max(xs)
    if mx - mn < 1e-9:
        return [0.5 for _ in xs]
    return [(x - mn) / (mx - mn) for x in xs]


def _cosine_sim(q: np.ndarray, M: np.ndarray) -> np.ndarray:
    qn = q / (np.linalg.norm(q) + 1e-9)
    Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    return Mn @ qn


def retrieve_with_fallback(
    query: str,
    chunks: List[str],
    k: int = 5,
    bm25_top_mult: int = DEFAULT_BM25_TOP_MULT,
    answer_threshold: float = 0.15,
    weight_bm25: float = DEFAULT_W_BM25,
    weight_embed: float = DEFAULT_W_EMBED,
) -> Tuple[List[int], List[str], float]:
    """
    Returns:
      - indices of selected chunks
      - selected chunk texts
      - best evidence score in [0,1] for answerability
    """
    if not chunks:
        return [], [], 0.0

    # 1) Keyword/BM25 as primary fallback
    bm25 = BM25(chunks)
    bm25_scores = bm25.score(query)
    topn = max(k * bm25_top_mult, min(len(chunks), 50))
    bm25_idx = np.argsort(bm25_scores)[::-1][:topn].tolist()

    # 2) Embedding-based results (if FAISS index exists and encoders available)
    faiss_idx: List[int] = []
    if load_index is not None and encode_query is not None and search_index is not None:
        idx = load_index()
        if idx is not None:
            q_emb = encode_query(query) 
            faiss_idx = search_index(q_emb, topn)
        else:
            q_emb = encode_query(query)
    else:
        q_emb = np.zeros((1, 1), dtype=np.float32)

    # 3) Candidate pool = union of bm25 and faiss candidates
    cand_idx = list(dict.fromkeys(bm25_idx + faiss_idx))  # preserve order

    # 4) Re-rank with embeddings among candidates; also compute lexical overlap
    cand_texts = [chunks[i] for i in cand_idx]
    qset = set(_tokenize(query))
    jacc_list = []
    for t in cand_texts:
        tset = set(_tokenize(t))
        inter = len(qset & tset)
        uni = len(qset | tset) or 1
        jacc_list.append(inter / uni)
    jacc = np.array(jacc_list, dtype=np.float32)

    if encode_texts is not None and q_emb.shape[1] > 1:
        cand_embs = encode_texts(cand_texts)
        q_vec = q_emb[0]
        sims = _cosine_sim(q_vec, cand_embs)
    else:
        sims = jacc.copy()

    bm25_norm = _normalize([bm25_scores[i] for i in cand_idx])
    sim_norm = _normalize(sims.tolist())

    combined = [weight_bm25 * b + weight_embed * s for b, s in zip(bm25_norm, sim_norm)]
    if combined and (max(combined) - min(combined) < 1e-6):
        combined = _normalize(jacc.tolist())
    order = np.argsort(combined)[::-1]
    final_idx = [cand_idx[i] for i in order[:k]]
    final_texts = [chunks[i] for i in final_idx]

    best_score = max(max(combined) if combined else 0.0, float(jacc.max()) if jacc.size else 0.0)

    # 5) Answerability check
    if best_score < answer_threshold:
        return [], [], float(best_score)

    return final_idx, final_texts, float(best_score)

import json
import re
from pathlib import Path
import pandas as pd
from llm_embedding import load_index, build_index
from retrieval import retrieve_with_fallback
from llm_generating import generate_answer
from table_linearizer import linearize
from save_jsonl import save_interaction
import sys

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent.parent

cfg = json.loads((ROOT / "config.json").read_text())

EXCEL_FILE = cfg.get("EXCEL_FILE")
K = cfg.get("K", 5)
ANSWERABILITY_THRESHOLD = cfg.get("ANSWERABILITY_THRESHOLD", 0.15)
EVIDENCE_OVERLAP_THRESHOLD = cfg.get("EVIDENCE_OVERLAP_THRESHOLD", 0.15)
D_WORD_LIMIT = int(cfg.get("DETAILED_WORD_LIMIT", 200))

_current_chunks: list[str] = []

def load_excel_data(excel_path: str) -> list[str]:
    """Load Excel data and return chunks"""
    sheets: dict[str, pd.DataFrame] = pd.read_excel(
        excel_path,
        sheet_name=None,
        engine="openpyxl"
    )

    chunks: list[str] = []
    for sheet_name, df in sheets.items():
        rows = linearize(df)
        tagged = [f"[{sheet_name}] {r}" for r in rows]
        chunks.extend(tagged)
    
    return chunks

def set_current_chunks(chunks: list[str]) -> None:
    """Set the current chunks to use for RAG pipeline"""
    global _current_chunks
    _current_chunks = chunks

def get_current_chunks() -> list[str]:
    """Get the current chunks"""
    global _current_chunks
    return _current_chunks

if __name__ == "__main__":
    
    chunks = load_excel_data(str(ROOT / EXCEL_FILE))
    print(f"Building FAISS index for {len(chunks)} snippets...")
    build_index(chunks)
    print("Index built successfully!")
    exit(0)


def _detect_intent(prompt: str) -> str:
    """Heuristic intent detection to tailor the detailed prompt.
    Returns one of: trend, compare, calc, superlative, lookup, explain, summary
    """
    p = (prompt or "").lower()
    # Comparison
    if any(k in p for k in ["compare", "versus", " vs ", "greater than", "less than", "higher than", "lower than"]):
        return "compare"
    # Trend / time evolution
    if any(k in p for k in ["trend", "evolution", "growth", "decline", "increase", "decrease", "over time"]):
        return "trend"
    # Superlative (max/min/top/bottom)
    if any(k in p for k in ["highest", "lowest", "max", "min", "top", "least", "maximum", "minimum"]):
        return "superlative"
    # Calculation / aggregation
    if any(k in p for k in [
        "sum", "average", "avg", "mean", "median", "total", "variance", "std", "standard deviation", "count"
    ]):
        return "calc"
    # Lookup / fact
    if any(k in p for k in ["what is", "value of", "lookup", "find", "return", "show"]):
        return "lookup"
    # Explain / why
    if any(k in p for k in ["why", "explain", "reason"]):
        return "explain"
    return "summary"


def _build_prompt(selected: list[str], prompt: str, detailed: bool) -> str:
    context = "\n\n".join(selected)
    if not detailed:
        return (
            "You are a helpful assistant. Use the following table snippets to answer the question concisely.\n\n"
            + context
            + f"\n\nQuestion: {prompt}\nAnswer:"
        )

    intent = _detect_intent(prompt)
    taxonomy = (
        "Operation taxonomy: aggregation (sum/avg/count), comparison (between entities), "
        "superlative (max/min/top), lookup (retrieve an exact value), trend (time-evolution), explain (reasons)."
    )
    base = [
        "You are a helpful financial table assistant.",
        "Use only the provided table snippets as evidence.",
        "If evidence is insufficient, reply with 'Insufficient evidence' and request a more specific query.",
        "Cite or reference the most relevant rows when helpful.",
        "Be accurate and avoid unsupported assumptions.",
        f"Keep the final answer under approximately {D_WORD_LIMIT} words while remaining clear.",
        taxonomy,
        "",
        context,
        "",
        f"Question: {prompt}",
        "",
        "First, implicitly decide the operation type from the taxonomy (no need to print it). Then answer accordingly.",
        "",
    ]

    if intent == "trend":
        tail = (
            "Provide a detailed trend analysis focused on:\n"
            "- Direction and magnitude of changes over time\n"
            "- Notable inflection points or anomalies (with dates)\n"
            "- Brief reasoning grounded in the data\n\nAnswer:"
        )
    elif intent == "compare":
        tail = (
            "Provide a detailed comparison that includes:\n"
            "- A short comparison of key metrics for each entity\n"
            "- The winner/better option per metric with a one-line rationale\n"
            "- Any caveats or missing data\n\nAnswer:"
        )
    elif intent == "superlative":
        tail = (
            "Provide a superlative-focused answer:\n"
            "- Identify the candidate rows\n"
            "- State the criterion and the max/min value with the entity/date\n"
            "- Show a single supporting line with values\n\nAnswer:"
        )
    elif intent == "calc":
        tail = (
            "Provide a calculation-oriented answer:\n"
            "- State the formula and variables used\n"
            "- Show minimal steps (1-3) with referenced values\n"
            "- Give the final numeric result with units/format\n\nAnswer:"
        )
    elif intent == "lookup":
        tail = (
            "Provide a precise fact-based answer:\n"
            "- Identify the exact row(s)/cell(s) used\n"
            "- Return the value(s) clearly\n\nAnswer:"
        )
    elif intent == "explain":
        tail = (
            "Provide a brief explanation grounded in data:\n"
            "- List 2-3 possible reasons supported by the table\n"
            "- Note uncertainties or missing fields if any\n\nAnswer:"
        )
    else:
        tail = (
            "Provide a detailed yet focused answer:\n"
            "- Key insights (bullet points)\n"
            "- Any anomalies or outliers\n"
            "- Short conclusion\n\nAnswer:"
        )

    return "\n".join(base) + tail


def rag_pipeline(prompt: str, detailed: bool = False, k: int | None = None) -> tuple[list[str], str]:
    k = k or K

    chunks = get_current_chunks()

    if not chunks:
        return [], "No data available. Please load an Excel file first."
    
    _ = load_index() 
    idxs, selected, best_score = retrieve_with_fallback(
        prompt,
        chunks,
        k=k,
        answer_threshold=ANSWERABILITY_THRESHOLD,
    )

    # If retrieval failed or evidence too weak, return standardized fallback
    if not selected:
        return [], "Insufficient evidence. Please provide more context or initialize data first."

    # Additional lightweight evidence coverage gate using query coverage
    STOP = {
        "the","a","an","is","are","to","of","and","in","on","for","by","with","at","from","as","it","this","that","be","or",
        "what","which","who","whom","whose","when","where","why","how"
    }
    def _norm_tok(t: str) -> str:
        t = t.lower()
        for suf in ("ing","ed","es","s"):
            if t.endswith(suf) and len(t) > 4:
                t = t[: -len(suf)]
                break
        syn = {"closing":"close","closed":"close","prices":"price"}
        return syn.get(t, t)

    def _tokens(s: str) -> list[str]:
        raw = [t for t in re.split(r"[^\w]+", (s or "").lower()) if t and len(t) > 2 and t not in STOP]
        return [_norm_tok(t) for t in raw]

    q_list = _tokens(prompt)
    qset = set(q_list)
    max_coverage = 0.0
    for s in selected:
        ts = _tokens(s)
        tset = set(ts)
        if not qset or not tset:
            continue
        matched = 0
        for qt in qset:
            if qt in tset:
                matched += 1
                continue
            if any((qt.startswith(tt) or tt.startswith(qt)) and len(qt) >= 4 and len(tt) >= 4 for tt in tset):
                matched += 1
        cov = matched / max(1, len(qset))
        if cov > max_coverage:
            max_coverage = cov

    if max_coverage < EVIDENCE_OVERLAP_THRESHOLD:
        return [], "Insufficient evidence. Please provide more context or initialize data first."

    full_prompt = _build_prompt(selected, prompt, detailed)

    answer = generate_answer(full_prompt, detailed)

    save_interaction(prompt, selected, answer)

    return selected, answer

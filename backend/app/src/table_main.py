import json
from pathlib import Path
import pandas as pd
from llm_embedding import encode_query, search_index, load_index
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

# Global variable to store current chunks
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
    from llm_embedding import build_index
    # Load default Excel file for standalone execution
    chunks = load_excel_data(str(ROOT / EXCEL_FILE))
    print(f"Building FAISS index for {len(chunks)} snippets...")
    build_index(chunks)
    print("Index built successfully!")
    exit(0)


def rag_pipeline(prompt: str, detailed: bool = False, k: int | None = None) -> tuple[list[str], str]:
    k = k or K

    chunks = get_current_chunks()

    if not chunks:
        return [], "No data available. Please load an Excel file first."
    
    index = load_index()
    if index is None:
        return [], "Index not available. Please initialize with an Excel file first."
    
    q_emb = encode_query(prompt)
    idxs = search_index(q_emb, k)
    selected = [chunks[i] for i in idxs]

    if detailed:
        full_prompt = (
            "You are a helpful assistant. Please provide a comprehensive and detailed analysis based on the following table data.\n\n"
            + "\n\n".join(selected)
            + f"\n\nQuestion: {prompt}\n\nPlease provide a detailed answer with:"
            + "\n- Analysis of the data"
            + "\n- Key insights and patterns"
            + "\n- Clear explanations and context"
            + "\n\nDetailed Answer:"
        )
    else:
        full_prompt = (
            "You are a helpful assistant. Use the following table snippets to answer the question concisely.\n\n"
            + "\n\n".join(selected)
            + f"\n\nQuestion: {prompt}\nAnswer:"
        )

    answer = generate_answer(full_prompt, detailed)

    save_interaction(prompt, selected, answer)

    return selected, answer

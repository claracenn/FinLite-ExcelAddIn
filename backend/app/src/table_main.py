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


sheets: dict[str, pd.DataFrame] = pd.read_excel(
    ROOT / EXCEL_FILE,
    sheet_name=None,
    engine="openpyxl"
)

chunks: list[str] = []
for sheet_name, df in sheets.items():
    rows = linearize(df)
    tagged = [f"[{sheet_name}] {r}" for r in rows]
    chunks.extend(tagged)

if __name__ == "__main__":
    from llm_embedding import build_index
    print(f"Building FAISS index for {len(chunks)} snippets...")
    build_index(chunks)
    print("Index built successfully!")
    exit(0)


def rag_pipeline(prompt: str, k: int | None = None) -> tuple[list[str], str]:
    k = k or K
    load_index()
    q_emb = encode_query(prompt)
    idxs = search_index(q_emb, k)
    selected = [chunks[i] for i in idxs]

    full_prompt = (
        "You are a helpful assistant. Use the following table snippets to answer the question.\n\n"
        + "\n\n".join(selected)
        + f"\n\nQuestion: {prompt}\nAnswer:"
    )

    answer = generate_answer(full_prompt)

    save_interaction(prompt, selected, answer)

    return selected, answer

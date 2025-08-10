import pandas as pd

def linearize(df: pd.DataFrame) -> list[str]:
    snippets = []
    for _, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in df.columns]
        snippets.append("; ".join(parts))
    return snippets

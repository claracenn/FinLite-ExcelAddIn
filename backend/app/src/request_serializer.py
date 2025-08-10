from datetime import datetime

def serialize_request(prompt: str, snippets: list[str], response: str) -> dict:
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "prompt": prompt,
        "snippets": snippets,
        "response": response
    }

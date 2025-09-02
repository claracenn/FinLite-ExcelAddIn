from datetime import datetime
from typing import Optional, List, Dict

def _utc_ts() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def serialize_request(
    prompt: str,
    snippets: List[str],
    response: str,
    *,
    session_id: Optional[str] = None,
    mode: str = "chat",
    meta: Optional[Dict] = None,
) -> dict:
    """Create a unified record for saving interactions.

    Fields:
      - timestamp: ISO8601 UTC timestamp
      - session_id: client-provided conversation id (optional)
      - mode: "chat" | "formula" | other
      - prompt/snippets/response: content payload
      - meta: optional extra info for future needs
    """
    return {
        "timestamp": _utc_ts(),
        "session_id": session_id if session_id else "",
        "mode": mode,
        "prompt": prompt,
        "snippets": snippets,
        "response": response,
        "meta": meta or {},
    }

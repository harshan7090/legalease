"""
history_store.py
────────────────
Save and load full session history as JSON files.
Allows users to download their session, re-upload it later, and continue.
"""

import json
import datetime


def session_to_json(history: list, confidence: float | None, metadata: dict | None = None) -> str:
    """Serialize a session to a JSON string for download."""
    payload = {
        "version": "1.0",
        "exported_at": datetime.datetime.now().isoformat(),
        "metadata": metadata or {},
        "last_confidence": confidence,
        "history": history,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def json_to_session(json_str: str) -> tuple[list, float | None, dict]:
    """
    Deserialize a previously exported session JSON.

    Returns
    -------
    (history, confidence, metadata) tuple.
    Raises ValueError if the JSON is invalid or missing required fields.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if "history" not in data:
        raise ValueError("JSON missing 'history' field.")

    history = data["history"]
    if not isinstance(history, list):
        raise ValueError("'history' must be a list.")

    confidence = data.get("last_confidence")
    metadata   = data.get("metadata", {})
    return history, confidence, metadata

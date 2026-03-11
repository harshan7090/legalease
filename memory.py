"""
memory.py
─────────
Manages the in-session conversation history for LegalEase.

Architecture
────────────
Conversation memory is stored in Streamlit's st.session_state dict.
This is an in-process Python dict that persists across Streamlit reruns
within a single browser tab, but resets when the tab is closed or the
server restarts.  This is perfect for a demo or single-user session.

For a production multi-user app you would replace session_state with a
database (e.g. Redis, SQLite, PostgreSQL) keyed by session ID.

Data model
──────────
history: list[dict]  — list of message objects, e.g.:
  [
    {"role": "user",      "content": "Here is my NDA clause: ..."},
    {"role": "assistant", "content": "This clause means ..."},
    ...
  ]

This format is directly compatible with the OpenAI/Groq messages API,
so it can be passed unchanged to client.chat.completions.create().
"""

import json
import streamlit as st

# Key used in st.session_state to store the history list.
_HISTORY_KEY = "legalease_history"
# Key used to persist the most recent confidence score.
_CONF_KEY = "legalease_last_conf"


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_memory() -> None:
    """
    Ensure the history and confidence keys exist in st.session_state.

    Must be called once at the top of app.py before any other memory
    functions.  Safe to call multiple times (idempotent).
    """
    # setdefault only sets the key if it doesn't already exist,
    # so this won't clear history on every Streamlit rerun.
    st.session_state.setdefault(_HISTORY_KEY, [])
    st.session_state.setdefault(_CONF_KEY, None)


# ─────────────────────────────────────────────────────────────────────────────
# Read / Write
# ─────────────────────────────────────────────────────────────────────────────

def get_history() -> list[dict]:
    """
    Return the full conversation history as a list of message dicts.

    Returns an empty list if memory has not been initialised yet.
    """
    return st.session_state.get(_HISTORY_KEY, [])


def add_turn(role: str, content: str) -> None:
    """
    Append a single message turn to the conversation history.

    Parameters
    ──────────
    role : str
        Either "user" or "assistant".  The Groq API rejects other values.
    content : str
        The message text.
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid role '{role}'. Must be 'user' or 'assistant'.")
    st.session_state[_HISTORY_KEY].append({"role": role, "content": content})


def set_confidence(score: float) -> None:
    """Persist the most recent confidence score so it survives reruns."""
    st.session_state[_CONF_KEY] = score


def get_confidence() -> float | None:
    """Return the last confidence score, or None if no turn has been made."""
    return st.session_state.get(_CONF_KEY)


def clear_memory() -> None:
    """
    Wipe the conversation history and last confidence score.

    Called when the user clicks "🗑️ Clear Chat" in the sidebar.
    """
    st.session_state[_HISTORY_KEY] = []
    st.session_state[_CONF_KEY] = None


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers (for export)
# ─────────────────────────────────────────────────────────────────────────────

def history_to_json() -> str:
    """
    Serialise the conversation history to a JSON string.

    Useful for debugging, logging, or implementing a persistent backend.

    Returns
    ───────
    str — pretty-printed JSON with 2-space indentation.
    """
    return json.dumps(get_history(), indent=2, ensure_ascii=False)


def history_turn_count() -> int:
    """Return the number of turns (user + assistant messages combined)."""
    return len(get_history())

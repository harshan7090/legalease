"""
groq_client.py
──────────────
Thin wrapper around the official Groq Python SDK.

Responsibilities
────────────────
1. Load credentials and settings from environment variables.
2. Expose a single public function `chat()` that sends a conversation to
   the Groq API and returns (response_text, confidence_score).
3. Expose a helper `estimate_confidence()` for the self-rating heuristic.

Why Groq?
─────────
Groq's LPU inference is dramatically faster than GPU-hosted alternatives,
making it ideal for interactive demos. The free tier gives ~14 000 tokens/min
on Llama 3 models — more than enough for a 90-minute session.

Swapping to a different provider
─────────────────────────────────
To switch to OpenAI-compatible endpoints (e.g. local Ollama, Together AI):
  1. Replace `from groq import Groq` with your client import.
  2. Replace `Groq(api_key=...)` with the new client constructor.
  3. Keep the `client.chat.completions.create(...)` call — most providers
     follow the OpenAI messages format.
  4. Update MODEL_NAME in .env.
"""

import os
import logging
from groq import Groq                # official SDK: pip install groq
from dotenv import load_dotenv       # loads .env into os.environ

# ── Logging setup ─────────────────────────────────────────────────────────────
# Module-level logger; Streamlit captures stdout so we log to stderr.
logger = logging.getLogger(__name__)

# ── Load environment ──────────────────────────────────────────────────────────
# load_dotenv() reads .env from the project root (where you run `streamlit run`).
# It is safe to call multiple times; subsequent calls are no-ops.
load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
# GROQ_API_KEY  — secret key from https://console.groq.com
# MODEL_NAME    — which Groq-hosted model to use (see .env.example for options)
# TEMPERATURE   — controls randomness; 0.3 gives focused legal analysis
# MAX_TOKENS    — cap on generated tokens to prevent runaway costs / latency
def _get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets (Streamlit Cloud) first, then os.environ (.env), then default."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

GROQ_API_KEY: str = _get_secret("GROQ_API_KEY", "")
MODEL_NAME:   str = _get_secret("MODEL_NAME", "llama-3.3-70b-versatile")
TEMPERATURE:  float = float(_get_secret("TEMPERATURE", "0.3"))
MAX_TOKENS:   int   = int(_get_secret("MAX_TOKENS", "1024"))

# ── Groq client instance ──────────────────────────────────────────────────────
# The Groq SDK client is stateless and thread-safe; one instance is fine.
# Raises groq.AuthenticationError at first API call if the key is invalid.
_client: Groq | None = None


def _get_client() -> Groq:
    """
    Lazily initialise and return the Groq client singleton.

    Lazy init means if the key is missing we fail at call-time with a clear
    error message rather than silently at import time.
    """
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. "
                "Copy .env.example → .env and add your key from https://console.groq.com"
            )
        # Groq(api_key=...) creates the HTTP session with auth headers.
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def chat(
    user_message: str,
    history: list[dict],
    system_prompt: str,
) -> tuple[str, float]:
    """
    Send a message to the Groq LLM and return (response_text, confidence_pct).

    Parameters
    ──────────
    user_message : str
        The user's latest input (already processed through a prompt template).
    history : list[dict]
        Previous turns as [{"role": "user"|"assistant", "content": str}, ...].
        This provides conversation memory — the model sees the full dialogue.
    system_prompt : str
        The fixed persona / instructions prepended to every conversation.

    Returns
    ───────
    tuple[str, float]
        response_text  — the model's generated reply.
        confidence_pct — estimated confidence as a percentage (0–100).

    Raises
    ──────
    EnvironmentError  — if GROQ_API_KEY is not configured.
    groq.APIError     — on network or API errors (caller should catch).
    """
    client = _get_client()

    # Build the messages list: system prompt + full history + new user message.
    # The OpenAI-compatible format requires role to be "system", "user",
    # or "assistant".  Groq follows this spec exactly.
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,                          # unpack previous turns
        {"role": "user", "content": user_message},
    ]

    # ── Primary completion ────────────────────────────────────────────────────
    # client.chat.completions.create() is a blocking HTTP call.
    # temperature=TEMPERATURE — lower values produce more deterministic output,
    #   which is preferable for legal analysis (fewer hallucinations).
    # max_tokens=MAX_TOKENS — hard cap; prevents unexpectedly long responses.
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    # Extract the text from the first (and only) choice.
    response_text: str = response.choices[0].message.content.strip()

    # ── Confidence estimation ─────────────────────────────────────────────────
    # Groq does not yet expose token log-probabilities through the SDK, so we
    # use a self-rating heuristic: ask the model to score its own certainty.
    confidence_pct: float = estimate_confidence(response_text)

    return response_text, confidence_pct


def estimate_confidence(analysis_text: str) -> float:
    """
    Ask the LLM to self-rate confidence in its own analysis (0–100).

    Heuristic rationale
    ───────────────────
    True probabilistic confidence requires access to token log-probs, which
    Groq does not currently expose via the SDK.  The next best option is to
    prompt the model to introspect: "How confident are you in this analysis?"
    Research (Kadavath et al., 2022; Xiong et al., 2024) shows that
    instruction-tuned LLMs produce well-calibrated self-assessments when asked
    directly, especially for factual / analytical tasks.

    We use temperature=0.0 for the confidence call so the score is
    deterministic and not influenced by sampling noise.

    Parameters
    ──────────
    analysis_text : str
        The LLM's primary response to be self-evaluated.

    Returns
    ───────
    float — confidence percentage clamped to [0, 100].
    """
    client = _get_client()

    # Minimal, deterministic prompt for self-rating.
    conf_messages = [
        {
            "role": "system",
            "content": (
                "You are a self-assessment engine. "
                "Reply with ONLY a single integer between 0 and 100. "
                "No words, no punctuation — just the number."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Rate your confidence (0–100) in the accuracy and completeness "
                f"of the following legal analysis:\n\n{analysis_text[:800]}"
                # Truncate to 800 chars to keep this call cheap and fast.
            ),
        },
    ]

    try:
        conf_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=conf_messages,
            temperature=0.0,    # fully deterministic
            max_tokens=5,       # we only need 1–3 digits
        )
        raw: str = conf_response.choices[0].message.content.strip()
        # Extract the first sequence of digits in case the model adds noise.
        import re
        match = re.search(r"\d+", raw)
        score = float(match.group()) if match else 72.0
        # Clamp to valid range.
        return max(0.0, min(100.0, score))

    except Exception as exc:
        # If the confidence call fails, return a conservative middle value.
        logger.warning("Confidence estimation failed: %s — using fallback 72.0", exc)
        return 72.0

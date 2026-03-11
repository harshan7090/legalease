"""
utils.py
────────
Utility functions for:
  • Confidence score formatting
  • Complexity Index calculation
  • Risk Badge generation (color + label + icon)
  • Reading-level computation (Flesch-Kincaid)
  • Keyword-based risk flag detection

These helpers are pure functions with no side effects — easy to unit test.
"""

import re
import textstat  # pip install textstat


# ─────────────────────────────────────────────────────────────────────────────
# Confidence & Complexity
# ─────────────────────────────────────────────────────────────────────────────

def complexity_index(confidence_pct: float) -> float:
    """
    Compute the Complexity Index from the confidence score.

    Formula
    ───────
        complexity = 100 − confidence

    Rationale: A model that is less confident is encountering language that
    is ambiguous, unusual, or genuinely complex.  The inverse relationship
    gives a single number the user can interpret as "how hard is this clause
    to understand?"

    Parameters
    ──────────
    confidence_pct : float — confidence in range [0, 100].

    Returns
    ───────
    float — complexity in range [0, 100].

    Example
    ───────
    >>> complexity_index(78.0)
    22.0
    """
    return round(100.0 - confidence_pct, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Badge
# ─────────────────────────────────────────────────────────────────────────────

# Threshold configuration — change these to tune the badge behaviour.
# LOW_THRESHOLD:    confidence ≥ this → LOW risk
# MEDIUM_THRESHOLD: confidence ≥ this → MEDIUM risk; else HIGH
LOW_THRESHOLD:    float = 75.0
MEDIUM_THRESHOLD: float = 50.0

# Risk levels → (hex color, icon)
_RISK_STYLES: dict[str, tuple[str, str]] = {
    "LOW":      ("#2e7d32", "🟢"),   # green  — clause seems standard
    "MEDIUM":   ("#f57c00", "🟡"),   # orange — some ambiguity, review carefully
    "HIGH":     ("#c62828", "🔴"),   # red    — model is uncertain; legal review essential
}


def risk_level(confidence_pct: float) -> str:
    """
    Map a confidence percentage to a risk level string.

    Mapping logic
    ─────────────
    confidence ≥ 75  →  LOW     (model is confident; clause is probably standard)
    confidence ≥ 50  →  MEDIUM  (some uncertainty; clauses worth discussing with counsel)
    confidence < 50  →  HIGH    (model is uncertain; strong legal review recommended)

    The inverse mapping makes intuitive sense for legal risk:
    high model confidence ≈ recognisable, standard language ≈ lower risk for non-expert.
    Low model confidence ≈ unusual or complex language ≈ higher stakes for non-expert.

    Parameters
    ──────────
    confidence_pct : float

    Returns
    ───────
    str — one of "LOW", "MEDIUM", "HIGH".
    """
    if confidence_pct >= LOW_THRESHOLD:
        return "LOW"
    elif confidence_pct >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


def risk_badge_html(confidence_pct: float, keyword_flags: list[str] | None = None) -> str:
    """
    Return an HTML snippet rendering a colored risk badge.

    The badge shows:
      • An emoji indicator (🟢 / 🟡 / 🔴)
      • The risk level label
      • The raw confidence percentage
      • Optional keyword flags detected in the clause text

    Parameters
    ──────────
    confidence_pct : float
        Confidence score from the LLM (0–100).
    keyword_flags : list[str] | None
        List of risky keywords found in the clause, if any.

    Returns
    ───────
    str — safe HTML string for st.markdown(..., unsafe_allow_html=True).
    """
    level = risk_level(confidence_pct)
    color, icon = _RISK_STYLES[level]
    complexity = complexity_index(confidence_pct)

    flags_html = ""
    if keyword_flags:
        items = "".join(f"<li>{f}</li>" for f in keyword_flags)
        flags_html = (
            f"<div style='margin-top:8px;font-size:12px;color:#555'>"
            f"<b>⚑ Detected risk terms:</b><ul style='margin:2px 0 0 16px'>{items}</ul>"
            f"</div>"
        )

    return (
        f"<div style='"
        f"  border:2px solid {color};"
        f"  border-radius:10px;"
        f"  padding:10px 16px;"
        f"  background:{color}18;"
        f"  margin:10px 0;"
        f"'>"
        f"  <div style='display:flex;justify-content:space-between;align-items:center'>"
        f"    <span style='font-size:18px;font-weight:700;color:{color}'>"
        f"      {icon} Risk Level: {level}"
        f"    </span>"
        f"    <span style='font-size:13px;color:#444'>"
        f"      Confidence: <b>{confidence_pct:.0f}%</b> &nbsp;|&nbsp; "
        f"      Complexity: <b>{complexity:.0f}</b>/100"
        f"    </span>"
        f"  </div>"
        f"  <div style='margin-top:6px'>"
        f"    <div style='background:#ddd;border-radius:6px;height:8px'>"
        f"      <div style='background:{color};width:{confidence_pct}%;height:100%;border-radius:6px;"
        f"           transition:width 0.8s ease'></div>"
        f"    </div>"
        f"  </div>"
        f"  {flags_html}"
        f"</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Keyword-based risk flags
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that frequently signal high-risk or unusual clause content.
# Extend this list to improve the heuristic flag detection.
_RISK_KEYWORDS: list[str] = [
    r"\bindemnif",           # indemnification obligations
    r"\bliabilit",           # liability (limitation or assumption)
    r"\bnon.compete",        # non-compete restrictions
    r"\bperpetual",          # perpetual license or obligation
    r"\birrevocable",        # irrevocable grant
    r"\bexclusive",          # exclusivity clauses
    r"\bwaive",              # waiver of rights
    r"\barbitration",        # mandatory arbitration (limits court access)
    r"\bclass.action",       # class action waiver
    r"\bgoverning law",      # choice-of-law (jurisdiction implications)
    r"\bliquidated damages", # predetermined damages
    r"\bforce majeure",      # force majeure (scope matters)
    r"\bassign",             # assignment of rights / IP
    r"\bintellectual property",
    r"\bconfidential",
]


def detect_risk_keywords(text: str) -> list[str]:
    """
    Scan clause or response text for known high-risk legal terms.

    Parameters
    ──────────
    text : str — the clause or LLM response text.

    Returns
    ───────
    list[str] — deduplicated list of matched keyword phrases.
    """
    text_lower = text.lower()
    found = set()
    for pattern in _RISK_KEYWORDS:
        # re.search returns a match object or None.
        match = re.search(pattern, text_lower)
        if match:
            # Use the matched string (stripped of regex anchors) as the label.
            found.add(match.group().strip().replace(".", "-"))
    return sorted(found)


# ─────────────────────────────────────────────────────────────────────────────
# Reading level
# ─────────────────────────────────────────────────────────────────────────────

def reading_level_label(text: str) -> str:
    """
    Return a human-readable reading-grade label for the given text.

    Uses the Flesch-Kincaid Grade Level formula, which outputs a U.S.
    school grade equivalent (e.g. 12 ≈ senior high school; 16+ ≈ college).

    Parameters
    ──────────
    text : str — the text to analyse (ideally 100+ words for accuracy).

    Returns
    ───────
    str — e.g. "Grade 10 — Moderate"
    """
    # textstat requires at least a few sentences; guard against tiny inputs.
    if len(text.split()) < 15:
        return "N/A (too short)"

    grade: float = textstat.flesch_kincaid_grade(text)

    if grade < 8:
        label = "Easy"
    elif grade < 12:
        label = "Moderate"
    else:
        label = "Complex"

    return f"Grade {grade:.0f} — {label}"

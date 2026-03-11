"""
utils.py
────────
Utility functions for risk scoring, badge generation, and text analysis.

Risk scoring approach (v2 - fixed)
────────────────────────────────────
The old approach used model confidence alone → always LOW because the model
is always confident in its answers regardless of clause danger.

New approach: CONTENT-BASED risk scoring
  1. Count HIGH-risk keywords in the user's input clause (indemnification,
     arbitration, non-compete, perpetual, irrevocable, etc.)
  2. Count MEDIUM-risk keywords
  3. Compute a risk_score from keyword counts
  4. Use confidence as a minor secondary signal only

This means a clause with "indemnify", "irrevocable", and "arbitration" will
correctly show HIGH RISK even if the model says it's 90% confident.
"""

import re
import textstat


# ─────────────────────────────────────────────────────────────────────────────
# Keyword risk tiers
# ─────────────────────────────────────────────────────────────────────────────

# HIGH-risk terms: each match adds 30 points to risk score
_HIGH_RISK_PATTERNS: list[tuple[str, str]] = [
    (r"\bindemnif",            "indemnification"),
    (r"\birrevocable",         "irrevocable"),
    (r"\bperpetual",           "perpetual"),
    (r"\bclass.action",        "class-action waiver"),
    (r"\barbitration",         "mandatory arbitration"),
    (r"\bnon.compet",          "non-compete"),
    (r"\bnon.solicit",         "non-solicitation"),
    (r"\bliquidated.damage",   "liquidated damages"),
    (r"\binjunctive.relief",   "injunctive relief"),
    (r"\bin.perpetuity",       "in perpetuity"),
    (r"\bwaive.*right",        "waiver of rights"),
    (r"\bunlimited.liabilit",  "unlimited liability"),
]

# MEDIUM-risk terms: each match adds 15 points to risk score
_MEDIUM_RISK_PATTERNS: list[tuple[str, str]] = [
    (r"\bliabilit",            "liability"),
    (r"\bexclusive",           "exclusivity"),
    (r"\bassign",              "assignment"),
    (r"\bintellectual.propert","intellectual property"),
    (r"\bconfidential",        "confidentiality"),
    (r"\bforce.majeure",       "force majeure"),
    (r"\bgoverning.law",       "governing law"),
    (r"\bjurisdiction",        "jurisdiction"),
    (r"\bterminat",            "termination"),
    (r"\bwaiv",                "waiver"),
    (r"\bpenalt",              "penalty"),
    (r"\bbreach",              "breach"),
    (r"\bdamage",              "damages"),
    (r"\bwarrant",             "warranty"),
    (r"\bindemnit",            "indemnity"),
]

# LOW / informational terms: flagged but don't add to score
_INFO_PATTERNS: list[tuple[str, str]] = [
    (r"\bconfidential",        "confidential"),
    (r"\bnotice",              "notice"),
    (r"\bgoverning",           "governing"),
    (r"\bpayment",             "payment"),
]


def detect_risk_keywords(text: str) -> list[str]:
    """Return deduplicated list of risk keyword labels found in text."""
    text_lower = text.lower()
    found = set()
    for pattern, label in (_HIGH_RISK_PATTERNS + _MEDIUM_RISK_PATTERNS):
        if re.search(pattern, text_lower):
            found.add(label)
    return sorted(found)


def compute_risk_score(clause_text: str, confidence_pct: float) -> float:
    """
    Compute a 0–100 risk score based on clause content + confidence.

    Formula:
        keyword_score = (high_count × 30) + (medium_count × 15)
        capped at 85 from keywords alone.
        confidence_penalty = max(0, (100 - confidence_pct) × 0.15)
        final = min(100, keyword_score + confidence_penalty)

    This means:
        0 high-risk + 0 medium-risk keywords  →  ~0–15   (LOW)
        1 medium-risk keyword                 →  ~15–25  (LOW-MEDIUM)
        2 medium-risk keywords                →  ~30–40  (MEDIUM)
        1 high-risk keyword                   →  ~30–40  (MEDIUM)
        2+ high-risk keywords                 →  ~60–85  (HIGH)
        3+ high-risk keywords                 →  ~85–100 (HIGH)
    """
    text_lower = clause_text.lower()
    high_count   = sum(1 for p, _ in _HIGH_RISK_PATTERNS   if re.search(p, text_lower))
    medium_count = sum(1 for p, _ in _MEDIUM_RISK_PATTERNS if re.search(p, text_lower))

    keyword_score = min(85.0, (high_count * 30) + (medium_count * 15))
    confidence_penalty = max(0.0, (100.0 - confidence_pct) * 0.15)
    final_score = min(100.0, keyword_score + confidence_penalty)
    return round(final_score, 1)


def risk_level(confidence_pct: float, clause_text: str = "") -> str:
    """
    Return risk level based on clause content (primary) + confidence (secondary).

    If clause_text is provided, uses content-based scoring.
    Falls back to confidence-only for backwards compatibility.
    """
    if clause_text.strip():
        score = compute_risk_score(clause_text, confidence_pct)
        if score >= 50:
            return "HIGH"
        elif score >= 20:
            return "MEDIUM"
        return "LOW"
    else:
        # Legacy fallback (confidence-only) — used when clause text not passed
        if confidence_pct < 50:
            return "HIGH"
        elif confidence_pct < 75:
            return "MEDIUM"
        return "LOW"


def complexity_index(confidence_pct: float) -> float:
    """Complexity = 100 - confidence. Higher = harder to understand."""
    return round(100.0 - confidence_pct, 1)


def reading_level_label(text: str) -> str:
    """Return Flesch-Kincaid reading grade label."""
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


# kept for any legacy callers that pass only confidence
def risk_badge_html(confidence_pct: float, keyword_flags: list | None = None) -> str:
    """Legacy wrapper — badge HTML used by old app.py callers."""
    level = risk_level(confidence_pct)
    color_map = {"LOW": "#00e676", "MEDIUM": "#ffa726", "HIGH": "#f44336"}
    color = color_map[level]
    return f"<div style='border:1px solid {color};border-left:3px solid {color};border-radius:8px;padding:12px 16px;background:{color}15'><b style='color:{color}'>{level} RISK</b> &nbsp; Confidence: {confidence_pct:.0f}%</div>"

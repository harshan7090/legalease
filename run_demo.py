"""
run_demo.py
───────────
Automated demo script — exercises all 4 LegalEase prompt templates against
a sample NDA non-compete clause and writes outputs to demo_outputs/.

Usage:
    python run_demo.py

Requirements:
    • .env file with GROQ_API_KEY set
    • pip install -r requirements.txt

Output files written to demo_outputs/:
    • explain_output.txt
    • summarize_output.txt
    • questions_output.txt
    • debug_output.txt
    • demo_report.pdf
    • demo_notes.md
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load env before importing groq_client ─────────────────────────────────────
load_dotenv()

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from prompts import TEMPLATES, build_prompt, SYSTEM_PROMPT
from groq_client import chat as groq_chat
from exports.pdf_export import generate_pdf, generate_markdown

# ── Sample clause (NDA non-compete) ──────────────────────────────────────────
SAMPLE_CLAUSE = """
Non-Compete and Non-Solicitation. During the term of this Agreement and for a period of
two (2) years following the termination or expiration thereof, for any reason, Employee
shall not, directly or indirectly, (i) engage in any business activity that competes with
the Company's Business within the Restricted Territory; (ii) solicit, induce, or attempt
to induce any employee, consultant, or contractor of the Company to terminate their
relationship with the Company; or (iii) solicit, divert, or attempt to divert any client,
customer, or business partner of the Company with whom Employee had material contact
during the twelve (12) months preceding termination. "Restricted Territory" means any
country, state, or province in which the Company conducts or has conducted business
during the twelve (12) months preceding termination. Employee acknowledges that the
restrictions herein are reasonable and necessary to protect the Company's legitimate
business interests, including its Confidential Information, client relationships, and
goodwill. In the event of a breach, the Company shall be entitled to seek injunctive
relief without the requirement to post bond, in addition to all other remedies available
at law or in equity.
""".strip()

DEBUG_BELIEF = (
    "If I work in a different city, a non-compete clause from my old employer "
    "cannot affect me because geography makes it unenforceable."
)

# ── Output directory ──────────────────────────────────────────────────────────
OUTPUT_DIR = Path("demo_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Run all 4 templates ────────────────────────────────────────────────────────
print("=" * 60)
print("LegalEase Demo Runner")
print("=" * 60)

results = {}          # store (response_text, confidence) per template
history = []          # accumulate turns for PDF export

template_inputs = {
    "📖 Explain":            SAMPLE_CLAUSE,
    "📋 Summarize":          SAMPLE_CLAUSE,
    "❓ Generate Questions": SAMPLE_CLAUSE,
    "🐛 Debug":              DEBUG_BELIEF,
}

for template_name, user_input in template_inputs.items():
    print(f"\n▶  Running template: {template_name}")
    prompt = build_prompt(template_name, user_input)

    try:
        response, confidence = groq_chat(
            user_message=prompt,
            history=history,
            system_prompt=SYSTEM_PROMPT,
        )
    except Exception as e:
        print(f"   ✗ Error: {e}")
        continue

    print(f"   ✓ Confidence: {confidence:.0f}%")
    print(f"   Response preview: {response[:120].replace(chr(10), ' ')}…")

    # Save individual output file
    slug = template_name.split()[-1].lower()
    out_file = OUTPUT_DIR / f"{slug}_output.txt"
    out_file.write_text(
        f"TEMPLATE: {template_name}\n"
        f"CONFIDENCE: {confidence:.0f}%\n"
        f"{'=' * 50}\n"
        f"INPUT:\n{user_input}\n\n"
        f"OUTPUT:\n{response}\n",
        encoding="utf-8",
    )
    print(f"   ✓ Written to {out_file}")

    # Accumulate for PDF
    history.append({"role": "user",      "content": f"[{template_name}]\n{user_input}"})
    history.append({"role": "assistant", "content": response})
    results[template_name] = (response, confidence)

# ── Export PDF ────────────────────────────────────────────────────────────────
print("\n▶  Generating PDF report…")
last_conf = list(results.values())[-1][1] if results else None
pdf_bytes = generate_pdf(history, confidence=last_conf)
pdf_path = OUTPUT_DIR / "demo_report.pdf"
pdf_path.write_bytes(pdf_bytes)
print(f"   ✓ Written to {pdf_path}")

# ── Export Markdown ───────────────────────────────────────────────────────────
print("▶  Generating Markdown notes…")
md_text = generate_markdown(history, confidence=last_conf)
md_path = OUTPUT_DIR / "demo_notes.md"
md_path.write_text(md_text, encoding="utf-8")
print(f"   ✓ Written to {md_path}")

print("\n✅ Demo run complete. See demo_outputs/ for all files.")

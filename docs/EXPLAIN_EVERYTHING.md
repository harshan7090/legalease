# LegalEase — Complete Technical Documentation
## `docs/EXPLAIN_EVERYTHING.md`

---

## Table of Contents

1. [Architecture & Data Flow](#1-architecture--data-flow)
2. [File-by-File Explanation](#2-file-by-file-explanation)
   - [app.py](#21-apppy)
   - [groq_client.py](#22-groq_clientpy)
   - [prompts.py](#23-promptspy)
   - [memory.py](#24-memorypy)
   - [utils.py](#25-utilspy)
   - [exports/pdf_export.py](#26-exportspdf_exportpy)
3. [Confidence Score & Complexity Index](#3-confidence-score--complexity-index)
4. [Risk Badge Mapping](#4-risk-badge-mapping)
5. [Swapping to a Different LLM Provider](#5-swapping-to-a-different-llm-provider)
6. [90-Minute Implementation Timeline](#6-90-minute-implementation-timeline)
7. [One-Minute Demo Script](#7-one-minute-demo-script)
8. [Test Plan & Sample Outputs](#8-test-plan--sample-outputs)
9. [Security & Privacy Checklist](#9-security--privacy-checklist)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Architecture & Data Flow

```
User (browser)
     │
     ▼
┌──────────────────────────────────────────────────────────┐
│  Streamlit (app.py)                                       │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ Sidebar  │  │ Chat Area   │  │ Export Buttons     │  │
│  │ template │  │ st.chat_    │  │ PDF / Markdown     │  │
│  │ selector │  │ message()   │  │                    │  │
│  └────┬─────┘  └──────┬──────┘  └─────────┬──────────┘  │
│       │               │                   │              │
│  prompts.py      memory.py           exports/            │
│  build_prompt()  get/add_turn()      pdf_export.py       │
│       │               │                                  │
│       └───────────────▼                                  │
│              groq_client.py                              │
│              chat()  ←→  Groq REST API (HTTPS)           │
│              estimate_confidence()                       │
│                    │                                     │
│               utils.py                                   │
│               risk_badge_html()                          │
│               detect_risk_keywords()                     │
└──────────────────────────────────────────────────────────┘
```

**Request lifecycle (one user message):**

1. User types a clause into `st.chat_input()`.
2. `app.py` calls `build_prompt(template, user_input)` → inserts user text into template string.
3. `app.py` calls `groq_chat(prompt, history, system_prompt)`:
   a. Assembles `[system] + [history] + [user]` messages list.
   b. POSTs to Groq REST API → gets `response_text`.
   c. Makes a second API call to self-rate confidence → gets `confidence_pct`.
4. `app.py` renders response with `st.chat_message()`.
5. `add_turn()` saves both turns to `st.session_state`.
6. `risk_badge_html(confidence)` renders the colored badge.
7. On export: `generate_pdf(history)` / `generate_markdown(history)` → bytes → download button.

---

## 2. File-by-File Explanation

### 2.1 `app.py`

The Streamlit entry-point. Re-executed top-to-bottom on every user interaction.

```python
load_dotenv()
```
**Line purpose:** Reads `.env` file and sets environment variables before any
module that needs `GROQ_API_KEY` is imported.  Must be first.

```python
st.set_page_config(page_title="⚖️ LegalEase", layout="wide", ...)
```
**Line purpose:** Configures the browser tab title, icon, and layout.
`layout="wide"` uses full browser width instead of the default narrow column.
**Must be the first Streamlit call** — Streamlit raises an error otherwise.

```python
with open(_css_path) as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)
```
**Block purpose:** Injects `static/style.css` into the page's `<head>`.
`unsafe_allow_html=True` is required because Streamlit sanitizes HTML by default.

```python
init_memory()
```
**Line purpose:** Ensures `st.session_state["legalease_history"]` and
`st.session_state["legalease_last_conf"]` exist before any widget tries to read them.
Without this, the first rerun would raise a `KeyError`.

```python
selected_template: str = st.radio(label="template_radio", options=TEMPLATE_NAMES, ...)
```
**Line purpose:** Renders four radio buttons in the sidebar.  The returned string
is exactly a key in `TEMPLATES`, so it can be passed directly to `build_prompt()`.

```python
for msg in get_history():
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
```
**Block purpose:** Replays the full conversation from session memory so the chat
area always shows all previous turns after a Streamlit rerun.

```python
user_input: str | None = st.chat_input(...)
```
**Line purpose:** Renders the sticky text input at the bottom of the page.
Returns `None` on every rerun where the user hasn't submitted; returns the
submitted string on the rerun triggered by pressing Enter.

```python
prompt: str = build_prompt(selected_template, user_input)
```
**Line purpose:** Wraps raw user text in the selected template before sending
to the API.  The chat display still shows raw `user_input` for readability.

```python
response_text, confidence = groq_chat(
    user_message=prompt, history=get_history(), system_prompt=SYSTEM_PROMPT
)
```
**Line purpose:** Single blocking API call.  Returns the LLM's response and
the self-rated confidence percentage.  Wrapped in try/except to handle missing
API key and network failures gracefully.

```python
st.rerun()
```
**Line purpose:** Forces Streamlit to re-execute `app.py` immediately after
adding turns to session state.  This ensures the new messages, badge, and
metrics render in the correct order.

---

### 2.2 `groq_client.py`

Handles all communication with the Groq API.

```python
_client: Groq | None = None
def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client
```
**Block purpose:** Singleton pattern.  Creates the Groq HTTP client once and
reuses it across all calls.  Lazy init means we only raise an error about
the missing API key when an actual call is made, not at import time.

```python
messages: list[dict] = [
    {"role": "system", "content": system_prompt},
    *history,
    {"role": "user", "content": user_message},
]
```
**Block purpose:** Constructs the full conversation context.  The `*history`
unpacks the list inline.  This is how conversation memory is implemented —
every turn is sent with every subsequent request.

```python
response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=messages,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
)
```
**Block purpose:** The actual API call.  `temperature=0.3` keeps legal analysis
focused and reduces hallucinations.  `max_tokens=1024` prevents runaway costs.

```python
raw = conf_response.choices[0].message.content.strip()
match = re.search(r"\d+", raw)
score = float(match.group()) if match else 72.0
return max(0.0, min(100.0, score))
```
**Block purpose:** Parses the confidence self-rating.  `re.search(r"\d+", raw)`
extracts the first number even if the model adds extra text.
`max(0.0, min(100.0, ...))` clamps the value to a valid range.
`72.0` is a conservative fallback — neither high nor low.

---

### 2.3 `prompts.py`

Contains all prompt strings.  No logic — just data and one helper function.

```python
SYSTEM_PROMPT: str = "You are LegalEase..."
```
**Line purpose:** Fixed persona prepended to every API call as the "system" message.
Includes the mandatory disclaimer instruction so every response ends with the warning.

```python
TEMPLATES: dict[str, str] = { "📖 Explain": "...", ... }
```
**Block purpose:** Maps display label → prompt template string.
Using emoji prefixes in keys makes the `st.radio()` options visually distinguishable.

```python
def build_prompt(template_name: str, user_input: str) -> str:
    template: str = TEMPLATES[template_name]
    return template.replace("{input}", user_input)
```
**Function purpose:** Simple `str.replace()` — safe for user input because we
are not using f-strings with `eval()` or format specifiers.  A `KeyError` here
means a programmer error (wrong template name), not user input error.

---

### 2.4 `memory.py`

Manages `st.session_state` for conversation history.

```python
st.session_state.setdefault(_HISTORY_KEY, [])
```
**Line purpose:** `setdefault` only sets the key if it does not already exist.
This is idempotent — calling `init_memory()` on every rerun does not wipe history.

```python
def add_turn(role: str, content: str) -> None:
    if role not in ("user", "assistant"):
        raise ValueError(...)
    st.session_state[_HISTORY_KEY].append({"role": role, "content": content})
```
**Function purpose:** Validates role before appending.  The Groq API raises an
error if role is anything other than "system", "user", or "assistant".

---

### 2.5 `utils.py`

Pure utility functions — no Streamlit calls, fully testable.

```python
def complexity_index(confidence_pct: float) -> float:
    return round(100.0 - confidence_pct, 1)
```
**Function purpose:** The Complexity Index is defined as `100 − confidence`.
This is a deliberate design choice: when the model is less confident, it is
encountering more ambiguous or complex language.  See §3 for full rationale.

```python
_RISK_STYLES: dict[str, tuple[str, str]] = {
    "LOW":    ("#2e7d32", "🟢"),
    "MEDIUM": ("#f57c00", "🟡"),
    "HIGH":   ("#c62828", "🔴"),
}
```
**Block purpose:** Maps risk level → (hex color, emoji).  Centralizing these
here means changing a color only requires editing one dict entry.

```python
def risk_badge_html(confidence_pct, keyword_flags=None) -> str:
```
**Function purpose:** Builds the HTML risk badge string.  Returns raw HTML
(not a Streamlit component) so it can be unit-tested without Streamlit running.

```python
_RISK_KEYWORDS: list[str] = [r"\bindemnif", r"\bliabilit", ...]
```
**Block purpose:** Regex patterns for legal risk terms.  `\b` is a word
boundary anchor — prevents "liability" matching inside "reliability".

---

### 2.6 `exports/pdf_export.py`

Generates PDF and Markdown from conversation history.

```python
class _LegalPDF(FPDF):
    def header(self): ...
    def footer(self): ...
```
**Class purpose:** Subclassing FPDF allows customising the header/footer on
every page.  fpdf2 calls these methods automatically when adding pages.

```python
pdf.set_auto_page_break(auto=True, margin=18)
```
**Line purpose:** Enables automatic page breaks when content reaches 18mm from
the bottom.  Without this, text would overflow off the page.

```python
raw = pdf.output()
if isinstance(raw, str):
    return raw.encode("latin-1")
return bytes(raw)
```
**Block purpose:** Handles fpdf2 version differences.  Older fpdf versions return
a latin-1 encoded string; fpdf2 returns bytes.  This guard works with both.

---

## 3. Confidence Score & Complexity Index

### Why not use token log-probabilities?

The ideal confidence measure is the **mean max-token probability** across the
generated sequence, derived from model logits:

```
confidence = mean( max_k softmax(logits_t)[k] for t in generated_tokens )
```

However, Groq's SDK does not currently expose `logprobs` in the response object.
(OpenAI supports `logprobs=True`; Groq may add this in future.)

### Self-rating heuristic (chosen approach)

We use a two-call approach:
1. Primary call → generates the legal analysis.
2. Secondary call (temperature=0.0) → asks the model to rate its own confidence.

**Research backing:** Kadavath et al. (2022) "Language Models (Mostly) Know What
They Know" showed that large instruction-tuned models produce well-calibrated
self-assessments when asked directly.  Calibration improves with model size —
Llama 3 70B will be better calibrated than 8B.

**Limitations:**
- Self-rating can be overconfident on hallucinated content.
- The secondary call doubles latency for every response.
- Not as reliable as true log-prob confidence for adversarial inputs.

### Complexity Index formula

```
Complexity = 100 − Confidence
```

**Rationale:** A model is less confident when the clause is:
- Using unusual or jurisdiction-specific language it was not trained on.
- Internally contradictory or ambiguous.
- Genuinely complex (nested conditions, defined terms within defined terms).

These are exactly the conditions that make a clause complex for a non-lawyer.
The inverse mapping therefore gives a useful proxy for "how hard is this clause
to understand?" without requiring a separate complexity model.

---

## 4. Risk Badge Mapping

| Confidence Range | Risk Level | Color | Meaning |
|-----------------|------------|-------|---------|
| ≥ 75%           | LOW        | 🟢 Green `#2e7d32` | Model recognizes standard language. Clause is likely routine but still worth reviewing. |
| 50–74%          | MEDIUM     | 🟡 Orange `#f57c00` | Some ambiguity detected. Discuss specific terms with a lawyer. |
| < 50%           | HIGH       | 🔴 Red `#c62828` | Model is uncertain. Clause may be unusual, complex, or highly jurisdiction-specific. Mandatory legal review. |

**Important caveat:** This badge is a heuristic signal, not a legal risk assessment.
A standard clause can have low confidence (e.g. if the model lacks training data
on a specific jurisdiction's boilerplate) and a genuinely risky clause can score
high confidence if it uses common legal phrasing.

The badge should be read as: *"How well does the AI understand this clause?"*
not *"How risky is this clause for you legally?"*

---

## 5. Swapping to a Different LLM Provider

### Option A: Different Groq model

Change one line in `.env`:
```
MODEL_NAME=llama3-70b-8192      # smarter, same speed
MODEL_NAME=mixtral-8x7b-32768   # longer context for lengthy contracts
```
No code changes needed.

### Option B: Local Ollama (Llama 3 or Mistral, fully private)

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3` or `ollama pull mistral`
3. In `groq_client.py`, replace:
```python
# BEFORE (Groq)
from groq import Groq
_client = Groq(api_key=GROQ_API_KEY)
response = client.chat.completions.create(model=MODEL_NAME, ...)
```
With:
```python
# AFTER (Ollama via openai-compatible endpoint)
from openai import OpenAI
_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
response = client.chat.completions.create(model="llama3", ...)  # or "mistral"
```
4. Install: `pip install openai`
5. Everything else (memory, exports, prompts) stays identical.

**Privacy note:** With Ollama, no data leaves your machine.

### Option C: OpenAI / Together AI / Anthropic

Replace the Groq client with the respective SDK.  The `messages` format
is identical for OpenAI-compatible providers.  For Anthropic:
```python
import anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
msg = client.messages.create(model="claude-3-haiku-20240307", max_tokens=1024,
      system=system_prompt, messages=history_without_system)
response_text = msg.content[0].text
```

---

## 6. 90-Minute Implementation Timeline

| Phase | Time | Tasks |
|-------|------|-------|
| **0 — Setup** | 0–10 min | `git init`, `pip install -r requirements.txt`, create `.env`, get Groq API key |
| **1 — Backend** | 10–30 min | Write `groq_client.py`, test with a single `chat()` call in terminal |
| **2 — Prompts** | 30–40 min | Write `prompts.py` with 4 templates; verify `build_prompt()` output |
| **3 — Memory** | 40–50 min | Write `memory.py`; manually verify `init_memory()` / `add_turn()` in REPL |
| **4 — UI** | 50–65 min | Write `app.py` skeleton: sidebar + chat loop + input box; run `streamlit run app.py` |
| **5 — Utils + Badge** | 65–75 min | Write `utils.py`; wire `risk_badge_html()` into `app.py` |
| **6 — Exports** | 75–83 min | Write `pdf_export.py`; wire both download buttons |
| **7 — Polish + Demo** | 83–90 min | Add CSS, test all 4 templates, run `run_demo.py`, rehearse demo script |

---

## 7. One-Minute Demo Script

> *What to say and click during the 60–90 second live demo:*

**[0:00]** Open the app. *"This is LegalEase — a privacy-first contract analyzer built
on Llama 3 running via Groq. No clause text leaves to a third-party; it goes to the
LLM API and comes back — or you can swap to a fully local model."*

**[0:10]** Paste the NDA non-compete clause from `demo_inputs/sample_ndas.md`.
Select **📖 Explain**. Hit Enter. *"Watch the AI translate this dense legal clause…"*

**[0:25]** Response appears. Point to the **🟡 MEDIUM risk badge**.
*"The Complexity Index here is 22 — that means this clause is relatively readable,
but the AI spotted 'restricted territory' and 'injunctive relief' as risk terms."*

**[0:35]** Switch sidebar to **📋 Summarize**. Type "summarize the same clause".
*"Now we get structured obligations, rights, and red flags in seconds."*

**[0:45]** Switch to **❓ Generate Questions**. Ask about the clause.
*"Five questions to ask your attorney before signing — generated instantly."*

**[0:52]** Click **📄 Download PDF Brief**. Open the file.
*"Professional PDF report — ready to share with a lawyer or keep for records."*

**[0:58]** *"The entire app runs locally in VS Code, uses only free-tier APIs,
and took 90 minutes to build. Thank you."*

---

## 8. Test Plan & Sample Outputs

### Manual test checklist

- [ ] Paste NDA clause → **Explain** → response in plain English, confidence displayed
- [ ] Same clause → **Summarize** → bullet points with red flags
- [ ] Same clause → **Generate Questions** → 5 numbered questions
- [ ] Type a misconception → **Debug** → misconception identified and corrected
- [ ] After 3+ turns, check that earlier turns appear in the chat history (memory working)
- [ ] Click **Download PDF** → file opens correctly in a PDF viewer
- [ ] Click **Download Notes** → valid Markdown file with all turns
- [ ] Click **🗑️ Clear Chat** → history wipes, badge disappears
- [ ] Start new session (refresh browser) → history is empty (session-only memory)
- [ ] Remove GROQ_API_KEY from .env → app shows friendly error, does not crash

### Expected confidence ranges (NDA non-compete clause)

| Template | Expected Confidence | Expected Risk Badge |
|----------|---------------------|---------------------|
| Explain | 75–85% | 🟢 LOW |
| Summarize | 78–88% | 🟢 LOW |
| Generate Questions | 80–90% | 🟢 LOW |
| Debug (misconception) | 70–82% | 🟢 LOW–🟡 MEDIUM |

*Note: Confidence varies per model and API call — ranges are approximate.*

---

## 9. Security & Privacy Checklist

**Before sending any real contract to this app, users should know:**

- [ ] **Data leaves your machine.** Clause text is sent to Groq's servers in the US.
      Groq's privacy policy governs how they handle this data.
- [ ] **Groq may log requests.** Check https://groq.com/privacy for current policy.
- [ ] **Never paste contracts with PII.** Redact names, SSNs, account numbers before analysis.
- [ ] **NDA-protected documents:** Pasting confidential contract text to a third-party API
      may violate the NDA itself. Consult your legal counsel before doing so.
- [ ] **For true privacy:** Use Ollama locally (see §5 Option B) — no data leaves your machine.
- [ ] **API key security:** Never commit `.env` to git. The `.gitignore` excludes it.
- [ ] **Output is not legal advice.** The app's disclaimer must be shown to all users.
- [ ] **No authentication.** The default Streamlit app has no login — do not deploy
      publicly without adding authentication.

---

## 10. Troubleshooting

### ❌ `EnvironmentError: GROQ_API_KEY is not set`
**Fix:** Copy `.env.example` → `.env` and paste your key from https://console.groq.com.
Run `cat .env` to verify the key is present.

### ❌ `groq.AuthenticationError: Invalid API key`
**Fix:** Your key may be expired or malformed.  Generate a new key at console.groq.com.
Ensure there are no extra spaces in `.env`.

### ❌ `groq.RateLimitError`
**Fix:** Groq free tier has token-per-minute limits.  Wait 60 seconds and retry.
Switch to `llama3-8b-8192` (faster, fewer tokens) if hitting limits on 70B.

### ❌ PDF download button produces a corrupted file
**Fix:** Ensure `fpdf2` (not the older `fpdf`) is installed: `pip install fpdf2`.
The older `fpdf` package has an incompatible API.

### ❌ `ModuleNotFoundError: No module named 'groq'`
**Fix:** Run `pip install -r requirements.txt` from the project root with your
virtual environment activated.

### ❌ CSS not loading (sidebar not dark)
**Fix:** Streamlit's CSS injection occasionally requires a hard browser refresh
(Ctrl+Shift+R / Cmd+Shift+R).  Also verify `static/style.css` exists.

### ❌ Chat history disappears on browser refresh
**Expected behavior.** `st.session_state` is per-tab and per-server-run.
For persistent memory, implement SQLite storage using the pattern in the
`memory.py` docstring.

### ❌ `textstat` raises `ZeroDivisionError` on short text
**Fix:** Already handled in `utils.py` — `reading_level_label()` returns
"N/A (too short)" for inputs under 15 words.

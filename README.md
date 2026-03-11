# ⚖️ LegalEase — Contract Clause Analyzer & Plain-English Translator

> An AI-powered legal assistant that translates contract clauses into plain English, identifies risks, and generates lawyer questions — built with Llama 3 (via Groq) + Streamlit.

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![Groq](https://img.shields.io/badge/LLM-Groq%20%2F%20Llama%203-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ⚠️ Disclaimer

This tool is for **educational and informational purposes only**.  
It does **not** constitute legal advice.  
Always consult a licensed attorney before making legal decisions.

---

## 🚀 Quick Start (VS Code, 5 minutes)

### Prerequisites

- Python 3.10 or later
- A free [Groq API key](https://console.groq.com) (takes ~2 minutes to get)
- VS Code (recommended) or any terminal

### Step 1 — Clone / open the project

```bash
# If you have git:
git clone <your-repo-url> legalease
cd legalease

# Or just open the folder in VS Code:
code .
```

### Step 2 — Create a virtual environment

```bash
# In the VS Code terminal (Ctrl+` to open):
python -m venv .venv

# Activate it:
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure your Groq API key

```bash
# Copy the example file:
cp .env.example .env

# Open .env and fill in your key:
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
# MODEL_NAME=llama-3.3-70b-versatile
```

> Get your free API key at: https://console.groq.com → **API Keys** → **Create API Key**

### Step 5 — Run the app

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## 📁 Project Structure

```
legalease/
├── app.py                    ← Streamlit UI (entry point)
├── prompts.py                ← 4 prompt templates + system prompt
├── groq_client.py            ← Groq API wrapper (LLM calls + confidence)
├── memory.py                 ← Conversation memory (st.session_state)
├── utils.py                  ← Risk badge, complexity index, reading level
├── exports/
│   ├── __init__.py
│   └── pdf_export.py         ← PDF + Markdown export generation
├── static/
│   └── style.css             ← Custom UI styles (injected into Streamlit)
├── demo_inputs/
│   └── sample_ndas.md        ← Sample clauses + expected outputs for testing
├── demo_outputs/             ← (created at runtime) output files from run_demo.py
├── docs/
│   └── EXPLAIN_EVERYTHING.md ← Line-by-line technical documentation
├── run_demo.py               ← Automated demo: exercises all 4 templates
├── requirements.txt
├── .env.example              ← Template for your .env file
├── .gitignore
├── Dockerfile                ← Optional Docker container
├── .devcontainer/
│   └── devcontainer.json     ← VS Code Dev Container config
└── README.md                 ← This file
```

---

## 🎛️ Choosing a Groq Model

Edit `MODEL_NAME` in your `.env` file:

| Model | Speed | Quality | Context | Best for |
|-------|-------|---------|---------|----------|
| `llama-3.3-70b-versatile` | ⚡⚡⚡ Fastest | Good | 8k tokens | **Default** — demos, fast iteration |
| `llama-3.1-70b-versatile` | ⚡⚡ Fast | **Excellent** | 8k tokens | Best analysis quality |
| `mixtral-8x7b-32768` | ⚡⚡ Fast | Very good | **32k tokens** | Long contracts (multi-page) |

> **Recommendation for demos:** Start with `llama-3.3-70b-versatile` for speed.  
> Switch to `llama-3.1-70b-versatile` if analysis quality needs to impress.

---

## 🔑 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Your Groq API key from console.groq.com |
| `MODEL_NAME` | `llama-3.3-70b-versatile` | Groq model to use (see table above) |
| `TEMPERATURE` | `0.3` | Response randomness (0=deterministic, 1=creative) |
| `MAX_TOKENS` | `1024` | Max tokens per response |

---

## 🧪 Testing the App

### Manual test with sample NDA clause

1. Open `demo_inputs/sample_ndas.md` and copy the **Sample Clause 1** text.
2. Paste it into the LegalEase chat input.
3. Try each template and compare with the expected outputs in that file.

### Automated demo runner

Exercises all 4 templates automatically and writes outputs to `demo_outputs/`:

```bash
python run_demo.py
```

Expected output:
```
==============================
LegalEase Demo Runner
==============================

▶  Running template: 📖 Explain
   ✓ Confidence: 81%
   ✓ Written to demo_outputs/explain_output.txt

▶  Running template: 📋 Summarize
   ...

✅ Demo run complete. See demo_outputs/ for all files.
```

---

## 📤 Exporting Results

The app offers two export formats after any conversation:

| Format | Button | Use case |
|--------|--------|---------|
| **PDF Brief** | `📄 Download PDF Brief` | Share with lawyer, archive |
| **Markdown Notes** | `📝 Download Notes (.md)` | Notion, Obsidian, version control |

Both exports include the full conversation, confidence score, and risk level.

---

## 🔄 Switching to a Different LLM

### Local model (fully private — no data leaves your machine)

1. Install [Ollama](https://ollama.com): `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a model: `ollama pull llama3` or `ollama pull mistral`
3. In `groq_client.py`, make **two changes**:

```python
# Line 1 — change the import:
# BEFORE:
from groq import Groq
# AFTER:
from openai import OpenAI   # pip install openai

# Line 2 — change the client constructor:
# BEFORE:
_client = Groq(api_key=GROQ_API_KEY)
# AFTER:
_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

4. Update `.env`: `MODEL_NAME=llama3` (or `mistral`)
5. Everything else — memory, exports, prompts — stays identical.

### OpenAI GPT-4o

```python
from openai import OpenAI
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# MODEL_NAME=gpt-4o in .env
```

---

## 🔒 Security & Privacy Notes

> **Before pasting any real contract into this app, please read:**

- **Data leaves your machine** — clause text is sent to Groq's API servers.
- **Check Groq's privacy policy** at https://groq.com/privacy.
- **Redact sensitive information** (names, SSNs, financial figures) before analysis.
- **NDA-protected documents** — pasting to a third-party API may breach the NDA itself. Get legal advice first.
- **For complete privacy** — use the local Ollama setup above. Zero data leaves your machine.
- **No authentication** — the default Streamlit app has no login. Do not deploy publicly without adding auth.
- **API key** — never commit `.env` to git. It is excluded in `.gitignore`.

---

## 📚 Documentation

See **[docs/EXPLAIN_EVERYTHING.md](docs/EXPLAIN_EVERYTHING.md)** for:
- Full architecture diagram and data flow
- Line-by-line explanation of every major file
- Confidence Score heuristic rationale
- Risk Badge threshold mapping
- Step-by-step swap guide for other LLM providers
- Security checklist
- Troubleshooting guide

---

## 📋 Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| `streamlit` | ≥1.35.0 | Web UI framework |
| `groq` | ≥0.9.0 | Official Groq Python SDK |
| `python-dotenv` | ≥1.0.0 | Load `.env` into environment |
| `fpdf2` | ≥2.7.9 | Pure-Python PDF generation |
| `textstat` | ≥0.7.3 | Flesch-Kincaid reading grade |

---

## 🐳 Docker (Optional)

```bash
# Build:
docker build -t legalease .

# Run (pass API key as env var):
docker run -p 8501:8501 -e GROQ_API_KEY=your_key legalease
```

App available at http://localhost:8501.

---

## 🏗️ Development in VS Code Dev Container

Open the project in VS Code → click **"Reopen in Container"** when prompted.  
The dev container installs all dependencies automatically.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) file.
#   l e g a l e a s e 
 
 
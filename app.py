"""
app.py  —  LegalEase v3
Futuristic dark UI | 10 templates | PDF upload | Clause comparison |
Contract scorecard chart | Session save/load | Keyword highlighter |
Multi-clause batch mode | Full export suite
"""

import os, json, datetime
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from prompts    import TEMPLATE_NAMES, build_prompt, SYSTEM_PROMPT
from groq_client import chat as groq_chat
from memory     import (init_memory, get_history, add_turn,
                        set_confidence, get_confidence, clear_memory)
from utils      import risk_badge_html, detect_risk_keywords, reading_level_label, complexity_index
from exports.pdf_export import generate_pdf, generate_markdown
from pdf_reader  import extract_text_from_pdf, chunk_text
from history_store import session_to_json, json_to_session

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LegalEase AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #080b14 !important;
    color: #c8d0e0 !important;
}
.stApp { background: linear-gradient(135deg,#080b14 0%,#0d1220 50%,#080b14 100%) !important; }
section.main > div { padding-top: 1rem; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0a0e1a 0%,#0d1325 100%) !important;
    border-right: 1px solid #1a2540 !important;
}
section[data-testid="stSidebar"] * { color: #a8b8d0 !important; }
section[data-testid="stSidebar"] hr { border-color: #1a2540 !important; }

/* Headings */
h1 {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    letter-spacing: 3px !important;
    text-transform: uppercase;
    background: linear-gradient(90deg,#4fc3f7,#26c6da,#80deea) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    margin-bottom: 0 !important;
}
h2,h3 { font-family:'Rajdhani',sans-serif !important; color:#4fc3f7 !important; letter-spacing:1px; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family:'Rajdhani',sans-serif !important;
    font-size:13px !important;
    letter-spacing:1.5px !important;
    text-transform:uppercase !important;
    color:#3a6080 !important;
    border-bottom:2px solid transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color:#4fc3f7 !important;
    border-bottom:2px solid #4fc3f7 !important;
}
[data-testid="stTabs"] { border-bottom: 1px solid #1a2540; }

/* Chat */
[data-testid="stChatMessage"] { border-radius:10px; padding:4px 10px; margin-bottom:6px; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background:rgba(79,195,247,0.05); border:1px solid rgba(79,195,247,0.15);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background:rgba(13,19,37,0.8); border:1px solid rgba(38,198,218,0.2);
}
[data-testid="stChatMessage"] p { font-size:14px !important; line-height:1.7 !important; color:#c8d0e0 !important; }

/* Chat input */
[data-testid="stChatInput"] { background:rgba(13,19,37,0.9) !important; border:1px solid rgba(79,195,247,0.3) !important; border-radius:12px !important; }
[data-testid="stChatInput"] textarea { background:transparent !important; color:#e0e8f0 !important; font-size:14px !important; border:none !important; caret-color:#4fc3f7 !important; }
[data-testid="stChatInput"] textarea::placeholder { color:#3a5070 !important; }

/* Metrics */
[data-testid="stMetric"] { background:rgba(13,19,37,0.8); border:1px solid rgba(79,195,247,0.2); border-radius:10px; padding:16px 20px; position:relative; overflow:hidden; }
[data-testid="stMetric"]::before { content:''; position:absolute; top:0;left:0; width:3px;height:100%; background:linear-gradient(180deg,#4fc3f7,#26c6da); border-radius:10px 0 0 10px; }
[data-testid="stMetricLabel"] { color:#5a7a9a !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
[data-testid="stMetricValue"] { color:#4fc3f7 !important; font-family:'JetBrains Mono',monospace !important; font-size:1.5rem !important; }

/* Buttons */
.stDownloadButton button {
    background:linear-gradient(135deg,rgba(79,195,247,0.1),rgba(38,198,218,0.1)) !important;
    color:#4fc3f7 !important; border:1px solid rgba(79,195,247,0.4) !important;
    border-radius:8px !important; font-family:'Rajdhani',sans-serif !important;
    font-size:13px !important; font-weight:600 !important; letter-spacing:1px !important;
    text-transform:uppercase !important; transition:all 0.2s !important;
}
.stDownloadButton button:hover { border-color:#4fc3f7 !important; box-shadow:0 0 16px rgba(79,195,247,0.3) !important; }
button[kind="secondary"] { background:transparent !important; border:1px solid rgba(244,67,54,0.4) !important; color:#ef9a9a !important; border-radius:8px !important; font-family:'Rajdhani',sans-serif !important; letter-spacing:0.5px !important; }
button[kind="secondary"]:hover { border-color:#f44336 !important; box-shadow:0 0 12px rgba(244,67,54,0.25) !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    border:1px dashed rgba(79,195,247,0.3) !important;
    border-radius:10px !important;
    background:rgba(13,19,37,0.5) !important;
    padding:8px !important;
}

/* Text areas */
textarea {
    background:rgba(13,19,37,0.8) !important;
    border:1px solid rgba(79,195,247,0.2) !important;
    border-radius:8px !important;
    color:#c8d0e0 !important;
    font-family:'Inter',sans-serif !important;
    font-size:13px !important;
}
textarea:focus { border-color:rgba(79,195,247,0.5) !important; box-shadow:0 0 8px rgba(79,195,247,0.15) !important; }

/* Selectbox */
[data-testid="stSelectbox"] > div { background:rgba(13,19,37,0.8) !important; border:1px solid rgba(79,195,247,0.2) !important; border-radius:8px !important; }

/* Info / warning boxes */
.stAlert { border-radius:8px !important; }

/* Disclaimer */
.disclaimer-box { background:rgba(255,160,0,0.05); border:1px solid rgba(255,160,0,0.3); border-left:3px solid #ffa000; padding:10px 16px; border-radius:6px; font-size:12px; color:#ffcc80; margin-bottom:16px; letter-spacing:0.2px; }

/* Label style */
.section-label { color:#3a5070; font-size:11px; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px; font-family:'Rajdhani',sans-serif; }

hr { border-color:#1a2540 !important; }
.stCaption, small { color:#3a5070 !important; font-size:11px !important; }
code { font-family:'JetBrains Mono',monospace !important; background:rgba(79,195,247,0.08) !important; color:#80deea !important; padding:2px 6px; border-radius:4px; font-size:12px !important; }
</style>
""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────────
init_memory()
if "clause_log" not in st.session_state:
    st.session_state.clause_log = []   # list of {clause, template, confidence, timestamp}
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "compare_a" not in st.session_state:
    st.session_state.compare_a = ""
if "compare_b" not in st.session_state:
    st.session_state.compare_b = ""

# ── Helper: section heading ───────────────────────────────────────────────────
def section_label(text):
    st.markdown(f"<p class='section-label'>{text}</p>", unsafe_allow_html=True)

# ── Helper: neon divider ──────────────────────────────────────────────────────
def neon_divider():
    st.markdown(
        "<div style='height:1px;background:linear-gradient(90deg,transparent,#4fc3f7,#26c6da,transparent);margin:16px 0;border-radius:2px'></div>",
        unsafe_allow_html=True
    )

# ── Helper: render risk badge ─────────────────────────────────────────────────
def render_risk_block(conf, last_msg=""):
    from utils import risk_level
    level_map = {
        "LOW":    ("#00e676", "#00e67618", "LOW RISK"),
        "MEDIUM": ("#ffa726", "#ffa72618", "MODERATE RISK"),
        "HIGH":   ("#f44336", "#f4433618", "HIGH RISK"),
    }
    lvl = risk_level(conf, last_msg)  # content-based risk scoring
    col_hex, col_bg, lvl_label = level_map[lvl]
    flags = detect_risk_keywords(last_msg)
    complexity = complexity_index(conf)

    flag_html = ""
    if flags:
        items = "".join(
            f"<span style='background:rgba(244,67,54,0.1);border:1px solid rgba(244,67,54,0.3);color:#ef9a9a;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px 3px;display:inline-block'>{f}</span>"
            for f in flags
        )
        flag_html = f"<div style='margin-top:10px'><span style='color:#3a5070;font-size:11px;letter-spacing:1px'>RISK TERMS &nbsp;</span>{items}</div>"

    st.markdown(f"""
    <div style='background:{col_bg};border:1px solid {col_hex}40;border-left:3px solid {col_hex};border-radius:10px;padding:14px 20px;margin:12px 0;font-family:Rajdhani,sans-serif'>
        <div style='display:flex;justify-content:space-between;align-items:center'>
            <div>
                <span style='font-size:11px;color:#3a5070;letter-spacing:2px;text-transform:uppercase'>ANALYSIS RESULT</span><br>
                <span style='font-size:20px;font-weight:700;color:{col_hex};letter-spacing:2px'>{lvl_label}</span>
            </div>
            <div style='text-align:right'>
                <span style='font-size:11px;color:#3a5070;letter-spacing:1px;text-transform:uppercase;display:block'>CONFIDENCE</span>
                <span style='font-size:28px;font-weight:700;color:{col_hex};font-family:JetBrains Mono,monospace'>{conf:.0f}%</span>
            </div>
        </div>
        <div style='margin-top:10px;background:rgba(0,0,0,0.3);border-radius:4px;height:4px'>
            <div style='background:{col_hex};width:{conf}%;height:100%;border-radius:4px;box-shadow:0 0 8px {col_hex}'></div>
        </div>
        {flag_html}
    </div>
    """, unsafe_allow_html=True)

    if last_msg:
        reading = reading_level_label(last_msg)
        st.markdown(f"<span style='color:#3a5070;font-size:11px'>READING LEVEL: <span style='color:#4fc3f7'>{reading}</span></span>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    turns = len([m for m in get_history() if m["role"] == "user"])
    c1.metric("🎯 Confidence",  f"{conf:.0f}%")
    c2.metric("🔀 Complexity",  f"{complexity:.0f}/100")
    c3.metric("💬 Turns",       turns)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚖ LEGALEASE")
    st.markdown("<p style='color:#3a6080;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-top:-8px'>AI Contract Analyzer v3</p>", unsafe_allow_html=True)
    st.markdown("---")

    section_label("PROMPT TEMPLATE")
    selected_template: str = st.radio(
        label="template", options=TEMPLATE_NAMES, label_visibility="collapsed"
    )

    st.markdown("---")
    section_label("MODEL")
    model_name = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    st.markdown(f"<code style='background:rgba(79,195,247,0.08);color:#4fc3f7;padding:4px 8px;border-radius:4px;font-size:11px'>{model_name}</code>", unsafe_allow_html=True)
    st.caption("Change MODEL_NAME in .env")

    st.markdown("---")
    section_label("SESSION")
    if st.button("🗑  Clear Chat", use_container_width=True, type="secondary"):
        clear_memory()
        st.session_state.clause_log = []
        st.session_state.pdf_text = ""
        st.rerun()

    # Save session
    history = get_history()
    if history:
        session_json = session_to_json(
            history, get_confidence(),
            {"model": model_name, "template": selected_template}
        )
        st.download_button(
            "💾 Save Session",
            data=session_json,
            file_name=f"legalease_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
        )

    # Load session
    st.markdown("---")
    section_label("LOAD PREVIOUS SESSION")
    session_file = st.file_uploader("Upload .json session", type=["json"], label_visibility="collapsed")
    if session_file and st.button("📂 Restore Session", use_container_width=True):
        try:
            loaded_history, loaded_conf, loaded_meta = json_to_session(session_file.read().decode())
            clear_memory()
            for turn in loaded_history:
                add_turn(turn["role"], turn["content"])
            if loaded_conf:
                set_confidence(loaded_conf)
            st.success(f"Session restored: {len(loaded_history)} messages")
            st.rerun()
        except Exception as e:
            st.error(f"Could not load session: {e}")

    st.markdown("---")
    st.markdown("<p style='color:#2a4060;font-size:11px;line-height:1.6'>⚠ Not legal advice. Consult a licensed attorney before making legal decisions.</p>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:2px;background:linear-gradient(90deg,transparent,#4fc3f7,#26c6da,transparent);margin-bottom:12px;border-radius:2px'></div>", unsafe_allow_html=True)
st.title("⚖ LEGALEASE")
st.markdown("<p style='color:#3a6080;font-size:13px;letter-spacing:0.5px;margin-top:-8px;margin-bottom:12px'>AI-powered contract analysis · 10 specialized templates · PDF upload · Risk scoring</p>", unsafe_allow_html=True)

st.markdown("<div class='disclaimer-box'>⚠ <b>NOT LEGAL ADVICE.</b> This tool is for educational and informational purposes only. Always consult a licensed attorney.</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_chat, tab_pdf, tab_compare, tab_batch, tab_history = st.tabs([
    "💬 CHAT",
    "📄 PDF UPLOAD",
    "⚖️ COMPARE CLAUSES",
    "📦 BATCH SCAN",
    "📊 SESSION HISTORY",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ═════════════════════════════════════════════════════════════════════════════
with tab_chat:
    # Chat history display
    for msg in get_history():
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Risk badge
    last_conf = get_confidence()
    if last_conf is not None:
        history = get_history()
        last_ai = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
        neon_divider()
        # Use last user message (clause) for content-based risk scoring
        user_turns = [m["content"] for m in get_history() if m["role"] == "user"]
        last_clause = user_turns[-1] if user_turns else last_ai
        render_risk_block(last_conf, last_clause)
        neon_divider()

    # Export buttons (only if there's chat history)
    if get_history():
        col_pdf, col_md, col_json = st.columns(3)
        with col_pdf:
            try:
                pdf_bytes = generate_pdf(get_history(), confidence=get_confidence())
                st.download_button("📄 PDF Brief", pdf_bytes, "legalease_report.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"PDF error: {e}")
        with col_md:
            md_text = generate_markdown(get_history(), confidence=get_confidence())
            st.download_button("📝 Markdown", md_text, "legalease_notes.md", "text/markdown", use_container_width=True)
        with col_json:
            sj = session_to_json(get_history(), get_confidence())
            st.download_button("💾 JSON Session", sj, "legalease_session.json", "application/json", use_container_width=True)

        neon_divider()

    # Chat input
    user_input = st.chat_input("Paste a contract clause or ask a legal question…")
    if user_input:
        prompt = build_prompt(selected_template, user_input)
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                try:
                    response_text, confidence = groq_chat(
                        user_message=prompt,
                        history=get_history(),
                        system_prompt=SYSTEM_PROMPT,
                    )
                except EnvironmentError as e:
                    st.error(f"⚠ Config error: {e}"); st.stop()
                except Exception as e:
                    st.error(f"⚠ API error: {e}"); st.stop()
            st.markdown(response_text)

        add_turn("user", user_input)
        add_turn("assistant", response_text)
        set_confidence(confidence)

        # Log this clause for history tab
        st.session_state.clause_log.append({
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "template":   selected_template,
            "clause":     user_input[:120] + ("…" if len(user_input) > 120 else ""),
            "confidence": confidence,
        })
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — PDF UPLOAD
# ═════════════════════════════════════════════════════════════════════════════
with tab_pdf:
    st.markdown("### 📄 Upload a Contract PDF")
    st.markdown("<p style='color:#3a6080;font-size:13px'>Upload any PDF contract or legal document. LegalEase will extract the text and let you analyze it with any template.</p>", unsafe_allow_html=True)

    uploaded_pdf = st.file_uploader(
        "Drop a PDF here or click to browse",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_pdf:
        with st.spinner("Extracting text from PDF…"):
            extracted = extract_text_from_pdf(uploaded_pdf)

        if extracted.startswith("ERROR:"):
            st.error(extracted)
        else:
            st.session_state.pdf_text = extracted
            word_count = len(extracted.split())
            char_count = len(extracted)
            pages_est  = extracted.count("--- Page")

            # Stats row
            c1, c2, c3 = st.columns(3)
            c1.metric("📄 Pages Detected", pages_est or "?")
            c2.metric("📝 Words", f"{word_count:,}")
            c3.metric("🔤 Characters", f"{char_count:,}")

            neon_divider()

            # Preview
            with st.expander("📋 Preview extracted text", expanded=False):
                st.text_area("", value=extracted[:3000] + ("\n\n[… truncated for preview]" if len(extracted) > 3000 else ""), height=300, disabled=True, label_visibility="collapsed")

            neon_divider()

            # Choose chunk to analyze
            chunks = chunk_text(extracted, max_chars=5000)
            section_label("SELECT SECTION TO ANALYZE")

            if len(chunks) == 1:
                selected_chunk = chunks[0]
                st.info(f"Document fits in one analysis block ({len(selected_chunk):,} chars).")
            else:
                chunk_labels = [f"Section {i+1} ({len(c):,} chars)" for i, c in enumerate(chunks)]
                chunk_idx = st.selectbox("Document section:", range(len(chunks)), format_func=lambda i: chunk_labels[i])
                selected_chunk = chunks[chunk_idx]
                with st.expander("Preview this section"):
                    st.text(selected_chunk[:1000] + "…")

            neon_divider()
            section_label("CHOOSE ANALYSIS TYPE")

            pdf_template = st.selectbox("Template:", TEMPLATE_NAMES, key="pdf_template_select")

            if st.button("🔍 Analyze This Section", use_container_width=True):
                prompt = build_prompt(pdf_template, selected_chunk)
                with st.spinner("Analyzing document section…"):
                    try:
                        response_text, confidence = groq_chat(
                            user_message=prompt,
                            history=[],  # fresh context for PDF analysis
                            system_prompt=SYSTEM_PROMPT,
                        )
                    except Exception as e:
                        st.error(f"API error: {e}")
                        response_text, confidence = None, None

                if response_text:
                    neon_divider()
                    st.markdown("#### 🤖 Analysis Result")
                    st.markdown(response_text)
                    neon_divider()
                    render_risk_block(confidence, user_input)  # user clause drives risk level

                    # Send to chat memory too
                    add_turn("user", f"[PDF: {uploaded_pdf.name} — {pdf_template}]\n{selected_chunk[:500]}…")
                    add_turn("assistant", response_text)
                    set_confidence(confidence)
                    st.session_state.clause_log.append({
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "template":  pdf_template,
                        "clause":    f"[PDF] {uploaded_pdf.name[:60]}",
                        "confidence": confidence,
                    })

            # Full document scan button
            if len(chunks) > 1:
                neon_divider()
                st.markdown("#### 🚀 Full Document Scan")
                st.markdown(f"<p style='color:#3a6080;font-size:13px'>Scan all {len(chunks)} sections using <b>🚨 Red Flag Scanner</b> and compile a report.</p>", unsafe_allow_html=True)
                if st.button("🚨 Scan Entire Document for Red Flags", use_container_width=True):
                    all_results = []
                    progress = st.progress(0, text="Scanning…")
                    for i, chunk in enumerate(chunks):
                        progress.progress((i+1)/len(chunks), text=f"Scanning section {i+1}/{len(chunks)}…")
                        try:
                            prompt = build_prompt("🚨 Red Flag Scanner", chunk)
                            resp, conf = groq_chat(prompt, [], SYSTEM_PROMPT)
                            all_results.append(f"## Section {i+1}\n\n{resp}\n\n---")
                        except Exception as e:
                            all_results.append(f"## Section {i+1}\n\nError: {e}\n\n---")
                    progress.empty()

                    full_report = "\n\n".join(all_results)
                    neon_divider()
                    st.markdown("### 🚨 Full Document Red Flag Report")
                    st.markdown(full_report)
                    st.download_button(
                        "📥 Download Full Report (.md)",
                        data=full_report,
                        file_name=f"redflag_report_{uploaded_pdf.name}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
    else:
        st.markdown("""
        <div style='border:1px dashed rgba(79,195,247,0.2);border-radius:12px;padding:40px;text-align:center;color:#3a5070;margin-top:20px'>
            <div style='font-size:40px;margin-bottom:12px'>📄</div>
            <div style='font-family:Rajdhani,sans-serif;font-size:16px;letter-spacing:2px;text-transform:uppercase;color:#4fc3f7'>Upload a PDF to begin</div>
            <div style='font-size:12px;margin-top:8px'>Supports contracts, NDAs, agreements, terms of service</div>
        </div>
        """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE CLAUSES
# ═════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("### ⚖️ Side-by-Side Clause Comparison")
    st.markdown("<p style='color:#3a6080;font-size:13px'>Paste two versions of the same clause. LegalEase will compare them, identify changes, and tell you which version is more risky.</p>", unsafe_allow_html=True)

    neon_divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("<p style='font-family:Rajdhani,sans-serif;font-size:13px;color:#4fc3f7;letter-spacing:2px;text-transform:uppercase'>VERSION A — Original</p>", unsafe_allow_html=True)
        clause_a = st.text_area("Clause A", height=220, placeholder="Paste original clause here…", label_visibility="collapsed", key="compare_a_input")

    with col_b:
        st.markdown("<p style='font-family:Rajdhani,sans-serif;font-size:13px;color:#ffa726;letter-spacing:2px;text-transform:uppercase'>VERSION B — Revised</p>", unsafe_allow_html=True)
        clause_b = st.text_area("Clause B", height=220, placeholder="Paste revised clause here…", label_visibility="collapsed", key="compare_b_input")

    neon_divider()

    if st.button("🔍 Compare Now", use_container_width=True):
        if not clause_a.strip() or not clause_b.strip():
            st.warning("Please paste both clauses before comparing.")
        else:
            combined_input = f"CLAUSE A:\n{clause_a}\n\n---CLAUSE B---\n\nCLAUSE B:\n{clause_b}"
            prompt = build_prompt("⚖️ Compare Clauses", combined_input)
            with st.spinner("Comparing clauses…"):
                try:
                    response_text, confidence = groq_chat(prompt, [], SYSTEM_PROMPT)
                except Exception as e:
                    st.error(f"API error: {e}")
                    response_text, confidence = None, None

            if response_text:
                neon_divider()
                st.markdown("#### 📊 Comparison Result")
                st.markdown(response_text)
                neon_divider()
                render_risk_block(confidence, user_input)  # user clause drives risk level

                # Show quick word-diff stats
                words_a = set(clause_a.lower().split())
                words_b = set(clause_b.lower().split())
                added   = words_b - words_a
                removed = words_a - words_b
                cA, cB = st.columns(2)
                cA.metric("Words Added (B vs A)",   len(added))
                cB.metric("Words Removed (B vs A)", len(removed))

                add_turn("user", f"[COMPARE]\nA: {clause_a[:200]}…\nB: {clause_b[:200]}…")
                add_turn("assistant", response_text)
                set_confidence(confidence)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — BATCH SCAN
# ═════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.markdown("### 📦 Multi-Clause Batch Scanner")
    st.markdown("<p style='color:#3a6080;font-size:13px'>Paste multiple clauses separated by a blank line. LegalEase will scan each one and produce a risk summary table.</p>", unsafe_allow_html=True)

    neon_divider()
    batch_input = st.text_area(
        "Paste clauses (separate with blank line)",
        height=260,
        placeholder="Clause 1 text here...\n\nClause 2 text here...\n\nClause 3 text here...",
        label_visibility="collapsed",
    )

    batch_template = st.selectbox("Template for all clauses:", TEMPLATE_NAMES, key="batch_template")

    col_run, col_clear = st.columns([3, 1])
    run_batch = col_run.button("⚡ Run Batch Analysis", use_container_width=True)

    if run_batch:
        clauses = [c.strip() for c in batch_input.split("\n\n") if c.strip()]
        if not clauses:
            st.warning("No clauses detected. Separate clauses with a blank line.")
        else:
            st.markdown(f"**Scanning {len(clauses)} clause(s)…**")
            progress = st.progress(0)
            results = []

            for i, clause in enumerate(clauses):
                progress.progress((i+1)/len(clauses), text=f"Clause {i+1}/{len(clauses)}")
                try:
                    prompt = build_prompt(batch_template, clause)
                    resp, conf = groq_chat(prompt, [], SYSTEM_PROMPT)
                    from utils import risk_level
                    results.append({
                        "clause_num": i+1,
                        "preview":    clause[:80] + ("…" if len(clause) > 80 else ""),
                        "confidence": conf,
                        "risk":       risk_level(conf),
                        "response":   resp,
                    })
                except Exception as e:
                    results.append({
                        "clause_num": i+1,
                        "preview":    clause[:80],
                        "confidence": 0,
                        "risk":       "ERROR",
                        "response":   str(e),
                    })

            progress.empty()
            neon_divider()

            # Summary table
            st.markdown("#### 📋 Batch Results Summary")
            import pandas as pd
            df = pd.DataFrame([{
                "#":          r["clause_num"],
                "Preview":    r["preview"],
                "Confidence": f"{r['confidence']:.0f}%",
                "Risk Level": r["risk"],
            } for r in results])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Risk distribution chart
            try:
                import plotly.express as px
                risk_counts = df["Risk Level"].value_counts().reset_index()
                risk_counts.columns = ["Risk", "Count"]
                color_map = {"LOW": "#00e676", "MEDIUM": "#ffa726", "HIGH": "#f44336", "ERROR": "#9e9e9e"}
                fig = px.pie(
                    risk_counts, names="Risk", values="Count",
                    color="Risk", color_discrete_map=color_map,
                    title="Risk Distribution",
                    hole=0.5,
                )
                fig.update_layout(
                    paper_bgcolor="#0d1220", plot_bgcolor="#0d1220",
                    font=dict(color="#a8b8d0", family="Rajdhani"),
                    title_font=dict(size=14, color="#4fc3f7"),
                    legend=dict(font=dict(color="#a8b8d0")),
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass

            neon_divider()

            # Detailed results
            for r in results:
                risk_colors = {"LOW": "#00e676", "MEDIUM": "#ffa726", "HIGH": "#f44336", "ERROR": "#9e9e9e"}
                c = risk_colors.get(r["risk"], "#9e9e9e")
                with st.expander(f"Clause {r['clause_num']} — {r['risk']} — {r['preview'][:60]}"):
                    st.markdown(r["response"])

            # Download batch report
            batch_md = "# LegalEase Batch Analysis Report\n\n"
            for r in results:
                batch_md += f"## Clause {r['clause_num']} — {r['risk']} ({r['confidence']:.0f}%)\n"
                batch_md += f"> {r['preview']}\n\n{r['response']}\n\n---\n\n"

            st.download_button(
                "📥 Download Batch Report (.md)",
                data=batch_md,
                file_name="legalease_batch_report.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — SESSION HISTORY
# ═════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📊 Analysis History & Risk Trend")

    log = st.session_state.clause_log
    if not log:
        st.markdown("""
        <div style='border:1px dashed rgba(79,195,247,0.15);border-radius:12px;padding:40px;text-align:center;color:#3a5070;margin-top:20px'>
            <div style='font-size:36px;margin-bottom:10px'>📊</div>
            <div style='font-family:Rajdhani,sans-serif;font-size:15px;letter-spacing:2px;text-transform:uppercase;color:#4fc3f7'>No analysis history yet</div>
            <div style='font-size:12px;margin-top:6px'>Start analyzing clauses in the Chat tab</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Summary metrics
        confs = [r["confidence"] for r in log]
        avg_conf = sum(confs) / len(confs)
        from utils import risk_level
        high_risk = sum(1 for c in confs if risk_level(c) == "HIGH")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📋 Total Analyses", len(log))
        c2.metric("📈 Avg Confidence", f"{avg_conf:.0f}%")
        c3.metric("🔴 High Risk Found", high_risk)
        c4.metric("✅ Low Risk Found", sum(1 for c in confs if risk_level(c) == "LOW"))

        neon_divider()

        # Confidence trend chart
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(1, len(log)+1)),
                y=confs,
                mode='lines+markers',
                name='Confidence',
                line=dict(color='#4fc3f7', width=2),
                marker=dict(size=8, color=[
                    "#00e676" if risk_level(c)=="LOW" else "#ffa726" if risk_level(c)=="MEDIUM" else "#f44336"
                    for c in confs
                ], line=dict(color='#4fc3f7', width=1)),
                fill='tozeroy',
                fillcolor='rgba(79,195,247,0.05)',
            ))
            fig.add_hline(y=75, line_dash="dot", line_color="#00e676", annotation_text="LOW RISK threshold", annotation_font_color="#00e676")
            fig.add_hline(y=50, line_dash="dot", line_color="#f44336", annotation_text="HIGH RISK threshold", annotation_font_color="#f44336")
            fig.update_layout(
                title="Confidence Score Trend",
                paper_bgcolor="#0d1220", plot_bgcolor="#0d1220",
                font=dict(color="#a8b8d0", family="Rajdhani"),
                title_font=dict(size=14, color="#4fc3f7"),
                xaxis=dict(title="Analysis #", gridcolor="#1a2540", color="#3a6080"),
                yaxis=dict(title="Confidence %", range=[0,105], gridcolor="#1a2540", color="#3a6080"),
                margin=dict(t=40, b=30),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Fallback if plotly not installed
            st.bar_chart({f"#{i+1}": c for i, c in enumerate(confs)})

        neon_divider()

        # History table
        st.markdown("#### 📋 Analysis Log")
        import pandas as pd
        df = pd.DataFrame([{
            "Time":       r["timestamp"],
            "Template":   r["template"],
            "Clause":     r["clause"],
            "Confidence": f"{r['confidence']:.0f}%",
            "Risk":       risk_level(r["confidence"]),
        } for r in log])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download history CSV
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download History (.csv)",
            data=csv,
            file_name="legalease_history.csv",
            mime="text/csv",
            use_container_width=True,
        )

"""
pdf_reader.py
─────────────
Extracts text from uploaded PDF files using PyMuPDF (fitz).

Why PyMuPDF?
• No external binary needed (unlike pdftotext/poppler).
• Handles scanned PDFs better than pypdf.
• Fast and pure-Python installable.

Fallback: if PyMuPDF is not installed, falls back to a basic pypdf approach,
and if that fails too, returns a clear error message.
"""

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract all text from a Streamlit UploadedFile (PDF).

    Parameters
    ----------
    uploaded_file : streamlit.runtime.uploaded_file_manager.UploadedFile

    Returns
    -------
    str — extracted plain text, or an error message prefixed with "ERROR:".
    """
    try:
        import fitz  # PyMuPDF
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages.append(f"--- Page {page_num + 1} ---\n{text.strip()}")
        doc.close()
        full_text = "\n\n".join(pages)
        return full_text if full_text.strip() else "ERROR: No extractable text found. The PDF may be image-only (scanned)."

    except ImportError:
        # Fallback to pypdf if PyMuPDF not installed
        try:
            from pypdf import PdfReader
            import io
            uploaded_file.seek(0)
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"--- Page {i+1} ---\n{text.strip()}")
            full_text = "\n\n".join(pages)
            return full_text if full_text.strip() else "ERROR: No extractable text found."
        except ImportError:
            return "ERROR: PDF reading library not installed. Run: pip install PyMuPDF"
        except Exception as e:
            return f"ERROR: Could not read PDF — {e}"

    except Exception as e:
        return f"ERROR: PDF extraction failed — {e}"


def chunk_text(text: str, max_chars: int = 6000) -> list[str]:
    """
    Split long text into chunks that fit within the LLM context window.

    Splits on double-newlines (paragraph boundaries) where possible.
    Falls back to hard character splits if paragraphs are too long.

    Parameters
    ----------
    text     : full extracted text
    max_chars: max characters per chunk (default 6000 ≈ ~1500 tokens)

    Returns
    -------
    list[str] — list of text chunks.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current.strip())
            # If single paragraph exceeds limit, hard-split it
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i+max_chars])
            else:
                current = para

    if current.strip():
        chunks.append(current.strip())

    return chunks

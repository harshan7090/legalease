# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — LegalEase
# ─────────────────────────────────────────────────────────────────────────────
# Build:   docker build -t legalease .
# Run:     docker run -p 8501:8501 -e GROQ_API_KEY=your_key legalease
# ─────────────────────────────────────────────────────────────────────────────

# Slim Python base image — smaller than full python:3.11
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (Docker layer cache — avoids reinstalling
# packages if only app code changed)
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir keeps the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Create the demo_outputs directory (run_demo.py writes here)
RUN mkdir -p demo_outputs

# Streamlit listens on 8501 by default
EXPOSE 8501

# Disable Streamlit's file watcher in production (not needed in container)
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
# Disable Streamlit's browser auto-open
ENV STREAMLIT_SERVER_HEADLESS=true

# The Groq API key MUST be passed as an environment variable at runtime:
#   docker run -e GROQ_API_KEY=gsk_xxx ...
# Do NOT bake the key into the image.

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

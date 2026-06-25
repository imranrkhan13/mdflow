# ── Hugging Face Spaces Docker deployment for MindFlow backend ──────────────
# HF Spaces runs on port 7860, uses /tmp for writable storage,
# and builds from this Dockerfile automatically on every git push.

FROM python:3.11-slim

# Install system packages — ffmpeg is required for video encoding
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
        libsndfile1 \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces requires a non-root user with UID 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# Install Python dependencies as root first (faster layer caching)
# requirements.txt is at the repo root (same level as Dockerfile on HF Spaces)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code — backend/ subfolder only, so /app/app/main.py is correct
COPY --chown=user backend/ .

# Switch to non-root user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    # Point all temp/cache dirs to /tmp (the only writable dir on HF Spaces)
    TMPDIR=/tmp \
    TTS_CACHE=/tmp/tts_cache \
    HF_HOME=/tmp/hf_home \
    XDG_CACHE_HOME=/tmp/cache

# HF Spaces listens on port 7860
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

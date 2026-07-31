FROM python:3.11-slim AS base

# Prevent .pyc files, force stdout/stderr to be unbuffered (so Render logs show up live)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/app/.fastembed_cache

WORKDIR /app

# System deps needed by: psycopg2 (postgres), trafilatura/lxml (HTML parsing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image at build time.
# This runs once during `docker build`, not on every container boot —
# so cold starts on Render's free tier don't pay a network round-trip
# or risk failing if HuggingFace/fastembed's CDN is slow/unreachable.
# Must match EMBEDDING_MODEL_NAME in app/agents/embedding_agent.py exactly,
# and FASTEMBED_CACHE_PATH must match the cache_dir passed to TextEmbedding()
# at runtime, or it'll just re-download into a different path anyway.
RUN python -c "\
from fastembed import TextEmbedding; \
TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/.fastembed_cache')"

COPY . .

# Embeddings run locally via fastembed (ONNX runtime, no torch) using
# BAAI/bge-small-en-v1.5 — model weights are baked into the image above,
# so no download happens at container start.

# Alembic migrations run as a Render "pre-deploy" / release command, not baked into
# the image start — see render.yaml's preDeployCommand. Keeping migration and boot
# separate means a failed migration blocks the deploy instead of silently booting
# an app against a stale schema.

EXPOSE 8000

# Render sets $PORT; default to 8000 for local `docker run`.
# WEB_CONCURRENCY defaults to 1, not 2 — on a 512MB instance, each worker
# loads its own copy of the embedding model into memory. Two workers means
# two model instances resident at once, which is a fast way to OOM. Bump
# this only if you've confirmed headroom (check Render's memory metrics).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
FROM python:3.11-slim AS base

# Prevent .pyc files, force stdout/stderr to be unbuffered (so Render logs show up live)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

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

COPY . .

# Embeddings run via the OpenAI API (text-embedding-3-small) at request time —
# see app/agents/embedding_agent.py. No local model to bake into the image;
# OPENAI_API_KEY must be set in the environment (Render env vars) for this to work.
# There's no local-model cold-start tradeoff anymore, but each embedding call is
# now a network round-trip to OpenAI, so watch latency/rate limits under load.

# Alembic migrations run as a Render "pre-deploy" / release command, not baked into
# the image start — see render.yaml's preDeployCommand. Keeping migration and boot
# separate means a failed migration blocks the deploy instead of silently booting
# an app against a stale schema.

EXPOSE 8000

# Render sets $PORT; default to 8000 for local `docker run`.
# WEB_CONCURRENCY defaults to 1. Since there's no local model resident in memory
# anymore, you have more headroom than before to bump worker count on a small
# instance — but still confirm against Render's memory metrics before raising it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
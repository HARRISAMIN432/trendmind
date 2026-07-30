FROM python:3.11-slim AS base

# Prevent .pyc files, force stdout/stderr to be unbuffered (so Render logs show up live)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed by: psycopg2 (postgres), trafilatura/lxml (HTML parsing),
# sentence-transformers/torch (CPU wheels still need build-essential on slim images)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the sentence-transformers embedding model at build time so the
# first request in production doesn't pay a ~90MB download + cold-start cost.
# Wrapped in try/except + `|| true` so a Hugging Face Hub hiccup at build time
# can't block the whole deploy — worst case it just downloads lazily on first use.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('Embedding model cached.')" || echo "Embedding model pre-cache skipped (will lazy-load on first request)"

# Alembic migrations run as a Render "pre-deploy" / release command, not baked into
# the image start — see render.yaml's preDeployCommand. Keeping migration and boot
# separate means a failed migration blocks the deploy instead of silently booting
# an app against a stale schema.

EXPOSE 8000

# Render sets $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
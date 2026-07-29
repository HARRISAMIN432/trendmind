# TrendMind — Architecture

## Pipeline (LangGraph `StateGraph`)

```
┌────────────┐   ┌─────────┐   ┌────────────┐   ┌────────────┐
│ Collector  │──▶│ Cleaner │──▶│ Classifier │──▶│ Summarizer │
│ (RSS)      │   │(trafi-  │   │ (LLM)      │   │ (LLM)      │
│            │   │ latura) │   │            │   │            │
└────────────┘   └─────────┘   └────────────┘   └─────┬──────┘
                                                        ▼
┌────────────┐   ┌──────────────┐              ┌────────────┐
│ Store       │◀──│ Duplicate    │◀─────────────│ Embedder   │
│ (Postgres)  │   │ Detection    │              │ (local ST) │
└────────────┘   │ (cosine sim) │              └────────────┘
                  └──────────────┘
```

Each stage is an independent agent module (M02-M07); `pipeline_graph.py` (M08) wires them into one `StateGraph` with conditional edges and retry/error handling, so a failure in one article doesn't halt the batch.

## Data model

- **`sources`** — RSS feed / publication → one-to-many with `articles`
- **`articles`** — central table; columns map directly to pipeline stages (raw_content from Collector, clean_content from Cleaner, category from Classifier, embedding_id from Embedder, duplicate_of_id from Dedup)
- **`companies`** — entities extracted from articles, many-to-many via `article_companies`; powers Company Intelligence (M13)
- **`trends`** — LLM-generated cluster insights over a time window, many-to-many via `trend_articles`; powers Trend Analysis (M12)
- **`newsletter_entries`** — generated daily digests (M15), standalone

Vector embeddings themselves live in a local Chroma collection, not Postgres — Postgres stores the `embedding_id` pointer.

## API surface

| Endpoint group     | Module | Purpose                                                 |
| ------------------ | ------ | ------------------------------------------------------- |
| `/articles`        | M09    | CRUD + filtering/pagination                             |
| `/search`          | M10    | Semantic search via Chroma similarity                   |
| `/chat`            | M11    | RAG chat with citations                                 |
| `/trends`          | M12    | Cluster + LLM-summarize recent articles into trends     |
| `/companies`       | M13    | Aggregated company intelligence profiles                |
| `/graph`           | M14    | Knowledge graph nodes/edges (entity extraction)         |
| `/newsletter`      | M15    | Daily digest generation                                 |
| `/recommendations` | M16    | Content-based filtering from read history               |
| `/internal/*`      | M21    | Key-protected endpoints for scheduled/CI-triggered runs |
| `/health`          | M22    | Liveness check for Render                               |

## Frontend

Next.js app router pages: home feed (M17), article detail + chat widget (M18), search (M19), trends/company/knowledge-graph pages (M20). All server components fetch directly from the FastAPI backend at build/request time except the chat widget and "For You" recommendations tab, which are client-side.

## Deployment topology

```
GitHub repo
   │
   ├── push to master ──▶ Vercel ──▶ frontend (static + SSR)
   │                                     │
   │                                     ▼ calls
   ├── Render Blueprint ──▶ Docker build ──▶ backend (FastAPI) ──▶ Neon Postgres
   │                                              ▲
   └── GitHub Actions cron ──▶ POST /internal/run-pipeline (wakes free-tier dyno,
                                drives scheduled ingestion in production)
```

## Scheduling

Two independent paths (M21): in-process APScheduler for local/dev convenience, and a GitHub Actions cron workflow for production — chosen because Render's free tier spins down idle instances, and only an external trigger reliably wakes it back up on schedule.

## Hardening for public deploy

- CORS locked to explicit origins via `ALLOWED_ORIGINS` (no wildcard in production)
- Per-IP rate limiting on expensive endpoints (chat, search, recommendations) via `slowapi`
- `/internal/*` endpoints require an `X-Scheduler-Key` header matching `SCHEDULER_API_KEY`
- Dockerized backend with a dependency-free `/health` check for Render's health monitor
- Database migrations run as a pre-deploy step, not at container boot, so a bad migration blocks the deploy rather than corrupting a live instance

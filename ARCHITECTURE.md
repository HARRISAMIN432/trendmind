# DigestAI — Architecture

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

Each stage is an independent agent; `pipeline_graph.py` wires them into one `StateGraph` with conditional edges and retry/error handling, so a failure in one article doesn't halt the batch.

## Data model

- **`sources`** — RSS feed / publication → one-to-many with `articles`
- **`articles`** — central table; columns map directly to pipeline stages (raw_content from Collector, clean_content from Cleaner, category from Classifier, embedding_id from Embedder, duplicate_of_id from Dedup)
- **`companies`** — entities extracted from articles, many-to-many via `article_companies`; powers Company Intelligence
- **`trends`** — LLM-generated cluster insights over a time window, many-to-many via `trend_articles`; powers Trend Analysis
- **`newsletter_entries`** — generated daily digests, standalone

Vector embeddings themselves live in a local Chroma collection, not Postgres — Postgres stores the `embedding_id` pointer.

## API surface

| Endpoint group     | Purpose                                                 |
| ------------------ | ------------------------------------------------------- |
| `/articles`        | CRUD + filtering/pagination                             |
| `/search`          | Semantic search via Chroma similarity                   |
| `/chat`            | RAG chat with citations                                 |
| `/trends`          | Cluster + LLM-summarize recent articles into trends     |
| `/companies`       | Aggregated company intelligence profiles                |
| `/graph`           | Knowledge graph nodes/edges (entity extraction)         |
| `/newsletter`      | Daily digest generation                                 |
| `/recommendations` | Content-based filtering from read history               |
| `/internal/*`      | Key-protected endpoints for scheduled/CI-triggered runs |
| `/health`          | Liveness check for Render                               |

## Chat architecture (Self-RAG)

`/chat` is not a single retrieve-then-generate call — it's a LangGraph `StateGraph`
(`rag_service.py`) that routes and grades before generating, so retrieval only
happens when needed and irrelevant docs never reach the LLM's context.

```
                    ┌───────┐
                    │ Route │  needs_retrieval?
                    └───┬───┘
             ┌──────────┴──────────┐
             ▼ no                  ▼ yes
   ┌──────────────────┐   ┌─────────────────────┐
   │ Generate (direct) │   │ Retrieve + Grade     │
   │ conversational,    │   │ semantic_search →    │
   │ no corpus context  │   │ per-doc relevance    │
   └────────┬──────────┘   │ score (0.0–1.0)       │
             │              └──────────┬───────────┘
             │                         │
             │              ┌──────────┴──────────┐
             │              ▼ none ≥ 0.7           ▼ ≥1 doc ≥ 0.7
             │      ┌──────────────────┐   ┌────────────────────┐
             │      │ Generate          │   │ Generate (grounded) │
             │      │ (no-match)        │   │ filtered docs only, │
             │      │ "no relevant       │   │ cited answer with   │
             │      │ articles found"    │   │ ChatCitation list   │
             │      └────────┬──────────┘   └──────────┬──────────┘
             │                │                          │
             └────────────────┴──────────┬───────────────┘
                                          ▼
                                        END
```

**Nodes:**

- **Route** — LLM call (`RouteDecision` schema) decides if the question needs
  corpus retrieval at all, or can be answered conversationally (greetings,
  meta questions). Fails open toward retrieval if the call errors.
- **Retrieve + Grade** — `semantic_search` fetches candidates from Chroma
  (cosine similarity over whole-article embeddings), then a second LLM call
  (`RetrievalGrade`/`DocScore` schema) scores each candidate's relevance to
  the question independently. Docs scoring below `RELEVANCE_THRESHOLD` (0.7)
  are dropped before generation.
- **Generate (direct)** — no retrieval occurred; answers from the model's
  own knowledge for small talk, never presented as corpus-grounded.
- **Generate (no-match)** — retrieval happened but nothing cleared the
  relevance bar; returns an explicit "couldn't find relevant articles"
  response rather than guessing, and never falls back to a corpus-agnostic
  answer for a factual question.
- **Generate (grounded)** — the standard RAG path: filtered, relevant docs
  only, LLM synthesizes an answer (`ChatAnswer` schema) and reports which
  URLs it actually cited, mapped back to `ChatCitation` objects for the
  frontend's sources panel.

## Frontend

Next.js app router pages: home feed, article detail + chat widget, search, trends/company/knowledge-graph pages. All server components fetch directly from the FastAPI backend at build/request time except the chat widget and "For You" recommendations tab, which are client-side.

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

Two independent paths: in-process APScheduler for local/dev convenience, and a GitHub Actions cron workflow for production

## Hardening for public deploy

- CORS locked to explicit origins via `ALLOWED_ORIGINS` (no wildcard in production)
- Per-IP rate limiting on expensive endpoints (chat, search, recommendations) via `slowapi`
- `/internal/*` endpoints require an `X-Scheduler-Key` header matching `SCHEDULER_API_KEY`
- Dockerized backend with a dependency-free `/health` check for Render's health monitor
- Database migrations run as a pre-deploy step, not at container boot, so a bad migration blocks the deploy rather than corrupting a live instance

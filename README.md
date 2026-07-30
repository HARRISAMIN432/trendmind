# DigestAI — AI News Intelligence Platform

A multi-agent AI news intelligence platform: it collects AI news from RSS feeds, cleans and deduplicates it, classifies and summarizes it with an LLM, embeds it for semantic search, and exposes all of that through a RAG chat interface, trend/knowledge-graph analysis, and a Next.js frontend — built entirely on free-tier infrastructure.

**Live demo:** _add your deployed Vercel URL here_
**Demo video / GIF:** _add here_

---

## Why this project exists

Built as a hands-on portfolio project while transitioning from full-stack (MERN) development into AI engineering — the goal was to actually implement, not just read about, the core building blocks of a production-shaped AI system: multi-agent orchestration (LangGraph), RAG, semantic search over a vector store, and LLM-driven structured extraction — on a strict $0 budget.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full pipeline diagram, data model, and per-module breakdown.

At a glance:

```
RSS feeds → Collector → Cleaner → Classifier → Summarizer → Embedder → Dedup
                                                                          │
                                                                          ▼
                                              Neon Postgres  ◄────  LangGraph pipeline
                                                     │
                                                     ▼
                              FastAPI (articles / search / chat / trends /
                              companies / graph / newsletter / recommendations)
                                                     │
                                                     ▼
                                    Next.js frontend (feed, search, chat,
                                    trends, company profiles, knowledge graph)
```

## Tech stack

| Layer         | Choice                                                |
| ------------- | ----------------------------------------------------- |
| LLM           | Groq (Llama 3.1/3.3 70B), Gemini Flash as fallback    |
| Embeddings    | `sentence-transformers` (`all-MiniLM-L6-v2`), local   |
| Vector store  | Chroma (local, file-based)                            |
| Database      | Neon Postgres (serverless free tier)                  |
| Orchestration | LangGraph                                             |
| Backend       | FastAPI + SQLAlchemy 2.0 + Alembic                    |
| Frontend      | Next.js + Tailwind                                    |
| Scheduling    | APScheduler (dev) or GitHub Actions cron (production) |
| Deployment    | Backend → Render (Docker); Frontend → Vercel          |

## Project status

All 22 planned modules complete — full pipeline, all backend APIs, full frontend, scheduling, and this deployment/hardening pass.

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, GROQ_API_KEY, GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

## Deployment

- **Backend (Render):** this repo includes a `render.yaml` blueprint and `backend/Dockerfile`. Connect the repo as a Render Blueprint, then set the secret env vars (`DATABASE_URL`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `SCHEDULER_API_KEY`) in the dashboard — they're intentionally left unset in `render.yaml`.
- **Frontend (Vercel):** import the repo, set the root directory to `frontend/`, and set `NEXT_PUBLIC_API_BASE_URL` to the deployed Render URL. `frontend/vercel.json` handles build settings and basic security headers.
- **Scheduled ingestion in production:** Render's free tier spins the service down after ~15 min idle, so the in-process APScheduler (`ENABLE_SCHEDULER`) is left **off** in production. `.github/workflows/ingest.yml` (from M21) hits the deployed API's `/internal/*` endpoints on a cron schedule instead, which also wakes the free-tier dyno back up. Requires the `API_BASE_URL` and `SCHEDULER_API_KEY` repo secrets.
- **CORS/rate limiting:** production origins are locked down via `ALLOWED_ORIGINS`; public-facing endpoints are rate-limited via `RATE_LIMIT_PER_MINUTE`. See `backend/app/main_additions_m22.py` for the exact wiring.

## What I learned

_A few prompts to fill this in yourself, since it should be in your own voice for a resume/portfolio README:_

- What was the trickiest part of getting the LangGraph pipeline's state to flow correctly across 6+ nodes?
- What tradeoff did going all-free-tier force (e.g. Chroma instead of a managed vector DB, local embeddings instead of an embedding API) — and would you make the same call again?
- What would you do differently if you rebuilt this from scratch?

## Repo structure

```
backend/     FastAPI app, LangGraph pipeline, agents, models, migrations
frontend/    Next.js app (feed, search, chat, trends, companies, graph)
.github/     CI + scheduled ingestion workflows
render.yaml  Render deployment blueprint
```

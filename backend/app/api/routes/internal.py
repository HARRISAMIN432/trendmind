from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.article import Article
from app.schemas.article import ArticleCreate
from app.api.routes.articles import create_article
from app.graph.pipeline_graph import run_pipeline
from app.services.trend_service import generate_trends
from app.services.graph_service import build_graph
from app.services.newsletter_service import generate_newsletter

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_scheduler_key(x_scheduler_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.SCHEDULER_API_KEY:
        raise HTTPException(status_code=503, detail="SCHEDULER_API_KEY not configured")
    if x_scheduler_key != settings.SCHEDULER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Scheduler-Key header")


def _article_to_create_payload(article) -> ArticleCreate:
    return ArticleCreate(
        title=article.title,
        url=article.url,
        published_at=getattr(article, "published_at", None),
        raw_content=getattr(article, "raw_content", None),
        clean_content=getattr(article, "clean_content", None),
        source_id=getattr(article, "source_id", None),
        category=getattr(article, "category", None),
        sub_category=getattr(article, "sub_category", None),
        importance=getattr(article, "importance", None),
        summary_short=getattr(article, "summary_short", None),
        embedding_id=getattr(article, "embedding_id", None),
        duplicate_of_id=getattr(article, "duplicate_of_id", None),
        company_names=getattr(article, "company_names", []) or [],
    )


@router.post("/run-pipeline", dependencies=[Depends(_require_scheduler_key)])
def trigger_pipeline(db: Session = Depends(get_db)) -> dict:
    existing_urls = {row[0] for row in db.query(Article.url).all()}
    state = run_pipeline(existing_urls=existing_urls)
    articles = state.get("articles", []) if isinstance(state, dict) else getattr(state, "articles", [])

    stored = skipped = failed = 0
    for article in articles:
        try:
            create_article(_article_to_create_payload(article), db)
            stored += 1
        except HTTPException as exc:
            skipped += 1 if exc.status_code == 409 else 0
            failed += 0 if exc.status_code == 409 else 1
        except Exception:  # noqa: BLE001
            failed += 1

    return {"stored": stored, "skipped_duplicate": skipped, "failed": failed}


@router.post("/run-trends", dependencies=[Depends(_require_scheduler_key)])
def trigger_trends(db: Session = Depends(get_db)) -> dict:
    created, considered, clustered = generate_trends(db)
    return {"trends_created": len(created), "articles_considered": considered, "articles_clustered": clustered}


@router.post("/run-graph", dependencies=[Depends(_require_scheduler_key)])
def trigger_graph(db: Session = Depends(get_db)) -> dict:
    processed, nodes_created, edges_created, errors = build_graph(db)
    return {
        "articles_processed": processed,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "errors": errors,
    }


@router.post("/run-newsletter", dependencies=[Depends(_require_scheduler_key)])
def trigger_newsletter(db: Session = Depends(get_db)) -> dict:
    entry, top_story_count, trend_included = generate_newsletter(db)
    return {
        "digest_date": entry.digest_date.isoformat(),
        "top_story_count": top_story_count,
        "trend_included": trend_included,
    }
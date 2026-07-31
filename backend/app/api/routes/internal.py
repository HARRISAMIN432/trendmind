from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.article import Article
from app.models.source import Source
from app.schemas.article import ArticleCreate
from app.api.routes.articles import create_article
from app.graph.pipeline_graph import run_pipeline
from app.config.feeds import AI_NEWS_FEEDS
from app.services.trend_service import generate_trends
from app.services.graph_service import build_graph
from app.services.newsletter_service import generate_newsletter

logger = logging.getLogger("trendmind.internal")

router = APIRouter(prefix="/internal", tags=["internal"])

_FEEDS_BY_NAME = {feed.name: feed for feed in AI_NEWS_FEEDS}


def _require_scheduler_key(x_scheduler_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.SCHEDULER_API_KEY:
        raise HTTPException(status_code=503, detail="SCHEDULER_API_KEY not configured")
    if x_scheduler_key != settings.SCHEDULER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Scheduler-Key header")


def _resolve_source(db: Session, source_name: str | None) -> int | None:
    if not source_name:
        return None

    source = db.query(Source).filter(Source.name.ilike(source_name)).first()
    if source is not None:
        return source.id

    feed = _FEEDS_BY_NAME.get(source_name)
    if feed is None:
        logger.warning(
            "No matching feed config for source_name=%r - creating Source row "
            "with a placeholder rss_url. Check app/config/feeds.py if this "
            "keeps happening for a source that should be configured.",
            source_name,
        )
    source = Source(
        name=source_name,
        rss_url=getattr(feed, "rss_url", None) or f"https://unknown-source.invalid/{source_name}",
        homepage_url=getattr(feed, "homepage_url", None),
    )
    db.add(source)
    db.flush()
    return source.id


def _article_to_create_payload(db: Session, article) -> ArticleCreate:
    logger.warning(
        "PIPELINE ARTICLE ATTRS for url=%s: %s",
        getattr(article, "url", "<no url>"),
        {k: (v if not isinstance(v, str) or len(v) < 80 else v[:80] + "...")
         for k, v in vars(article).items()} if hasattr(article, "__dict__") else "no __dict__ (slots/dataclass?)",
    )

    payload = ArticleCreate(
        title=article.title,
        url=article.url,
        published_at=getattr(article, "published_at", None),
        raw_content=getattr(article, "raw_content", None),
        clean_content=getattr(article, "clean_content", None),
        source_id=_resolve_source(db, getattr(article, "source_name", None)),
        category=getattr(article, "category", None),
        sub_category=getattr(article, "sub_category", None),
        importance=getattr(article, "importance", None),
        summary_short=getattr(article, "summary_short", None),
        key_takeaway=getattr(article, "key_takeaway", None),
        why_it_matters=getattr(article, "why_it_matters", None),
        technical_highlights=getattr(article, "technical_highlights", None),
        embedding_id=getattr(article, "embedding_id", None),
        duplicate_of_id=getattr(article, "duplicate_of_id", None),
        company_names=getattr(article, "companies", []) or [],
    )

    logger.warning(
        "ARTICLE_CREATE PAYLOAD for url=%s: source_id=%s embedding_id=%s "
        "key_takeaway=%r why_it_matters=%r technical_highlights=%r company_names=%s",
        payload.url,
        getattr(payload, "source_id", "<FIELD MISSING FROM SCHEMA>"),
        getattr(payload, "embedding_id", "<FIELD MISSING FROM SCHEMA>"),
        getattr(payload, "key_takeaway", "<FIELD MISSING FROM SCHEMA>"),
        getattr(payload, "why_it_matters", "<FIELD MISSING FROM SCHEMA>"),
        getattr(payload, "technical_highlights", "<FIELD MISSING FROM SCHEMA>"),
        getattr(payload, "company_names", "<FIELD MISSING FROM SCHEMA>"),
    )
    return payload


@router.post("/run-pipeline", dependencies=[Depends(_require_scheduler_key)])
def trigger_pipeline(db: Session = Depends(get_db)) -> dict:
    print("I have arrived")
    existing_urls = {row[0] for row in db.query(Article.url).all()}
    state = run_pipeline(existing_urls=existing_urls)
    articles = state.get("articles", []) if isinstance(state, dict) else getattr(state, "articles", [])

    stored = skipped = failed = 0
    for article in articles:
        try:
            create_article(_article_to_create_payload(db, article), db)
            stored += 1
        except HTTPException as exc:
            db.rollback()
            print("STORE HTTP ERROR:", exc.status_code, exc.detail) 
            skipped += 1 if exc.status_code == 409 else 0
            failed += 0 if exc.status_code == 409 else 1
        except Exception as exc:  
            db.rollback()
            print("STORE ERROR:", repr(exc))  
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
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import HTTPException

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.graph.pipeline_graph import run_pipeline
from app.models.article import Article
from app.schemas.article import ArticleCreate
from app.api.routes.articles import create_article
from app.services.trend_service import generate_trends
from app.services.graph_service import build_graph
from app.services.newsletter_service import generate_newsletter

logger = logging.getLogger(__name__)

settings = get_settings()

scheduler = BackgroundScheduler(timezone="UTC")

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


def run_ingestion_job() -> None:
    db = SessionLocal()
    started = datetime.now(timezone.utc)
    stored = skipped = failed = 0
    try:
        existing_urls = {row[0] for row in db.query(Article.url).all()}

        state = run_pipeline(existing_urls=existing_urls)
        articles = state.get("articles", []) if isinstance(state, dict) else getattr(state, "articles", [])

        for article in articles:
            try:
                payload = _article_to_create_payload(article)
                create_article(payload, db)  # opens/commits its own transaction per call
                stored += 1
            except HTTPException as exc:
                if exc.status_code == 409:
                    # Already stored (URL race / dedup-hint miss) — not an error.
                    skipped += 1
                else:
                    failed += 1
                    logger.warning("Ingestion job: failed to store article: %s", exc.detail)
            except Exception:  # noqa: BLE001
                failed += 1
                logger.exception("Ingestion job: unexpected error storing an article")

        logger.info(
            "Ingestion job finished in %.1fs: %d stored, %d skipped (duplicate), %d failed",
            (datetime.now(timezone.utc) - started).total_seconds(), stored, skipped, failed,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Ingestion job: pipeline run failed")
    finally:
        db.close()

def run_trends_job() -> None:
    db = SessionLocal()
    try:
        created, considered, clustered = generate_trends(db)
        logger.info(
            "Trends job: %d trends created from %d considered articles (%d clustered)",
            len(created), considered, clustered,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Trends job failed")
    finally:
        db.close()


def run_graph_job() -> None:
    db = SessionLocal()
    try:
        processed, nodes_created, edges_created, errors = build_graph(db)
        logger.info(
            "Graph job: %d articles processed, %d nodes created, %d edges created, %d errors",
            processed, nodes_created, edges_created, len(errors),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Graph job failed")
    finally:
        db.close()

def run_newsletter_job() -> None:
    db = SessionLocal()
    try:
        entry, top_story_count, trend_included = generate_newsletter(db)
        logger.info(
            "Newsletter job: digest for %s generated, %d top stories, trend_included=%s",
            entry.digest_date, top_story_count, trend_included,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Newsletter job failed")
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=False) — skipping job registration.")
        return

    scheduler.add_job(
        run_ingestion_job,
        trigger=IntervalTrigger(hours=settings.PIPELINE_INTERVAL_HOURS),
        id="ingestion_pipeline",
        replace_existing=True,
        max_instances=1,  
        coalesce=True,    
    )
    scheduler.add_job(
        run_trends_job,
        trigger=IntervalTrigger(hours=settings.TRENDS_INTERVAL_HOURS),
        id="trend_generation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_graph_job,
        trigger=IntervalTrigger(hours=settings.GRAPH_INTERVAL_HOURS),
        id="graph_build",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_newsletter_job,
        trigger=CronTrigger(hour=settings.NEWSLETTER_HOUR_UTC, minute=0),
        id="newsletter_generation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started: pipeline every %sh, trends every %sh, graph every %sh, "
        "newsletter daily at %02d:00 UTC",
        settings.PIPELINE_INTERVAL_HOURS, settings.TRENDS_INTERVAL_HOURS,
        settings.GRAPH_INTERVAL_HOURS, settings.NEWSLETTER_HOUR_UTC,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
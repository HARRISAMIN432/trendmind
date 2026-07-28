from __future__ import annotations
import logging
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Sequence
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models.article import Article
from app.models.trend import Trend
from app.models.associations import trend_articles
from app.models.newsletterentry import NewsletterEntry

logger = logging.getLogger(__name__)

IMPORTANCE_RANK = {"High": 0, "Medium": 1, "Low": 2}
_UNRANKED = len(IMPORTANCE_RANK)


def _sort_key(article: Article) -> tuple[int, float]:
    rank = IMPORTANCE_RANK.get(article.importance or "", _UNRANKED)
    published_ts = article.published_at.timestamp() if article.published_at else 0.0
    return (rank, -published_ts)


def _get_top_stories(
    db: Session, window_start: datetime, window_end: datetime, limit: int
) -> list[Article]:
    articles = (
        db.query(Article)
        .options(joinedload(Article.source), joinedload(Article.companies))
        .filter(Article.duplicate_of_id.is_(None))  # M07 flag-not-filter contract, enforced here as in M09/M12
        .filter(Article.published_at >= window_start)
        .filter(Article.published_at < window_end)
        .all()
    )
    articles.sort(key=_sort_key)
    return articles[:limit]


def _get_biggest_trend(db: Session, window_start: datetime, window_end: datetime) -> Trend | None:
    count_col = func.count(trend_articles.c.article_id).label("article_count")
    row = (
        db.query(Trend.id, count_col)
        .join(trend_articles, trend_articles.c.trend_id == Trend.id)
        .filter(Trend.created_at >= window_start)
        .filter(Trend.created_at < window_end)
        .group_by(Trend.id)
        .order_by(count_col.desc(), Trend.created_at.desc())
        .first()
    )
    trend_id = row[0] if row is not None else None

    if trend_id is None:
        fallback = db.query(Trend.id).order_by(Trend.created_at.desc()).first()
        trend_id = fallback[0] if fallback is not None else None

    if trend_id is None:
        return None

    return (
        db.query(Trend)
        .options(joinedload(Trend.articles))
        .filter(Trend.id == trend_id)
        .first()
    )


def _render_markdown(
    digest_date: date_type, top_stories: Sequence[Article], trend: Trend | None
) -> str:
    lines: list[str] = [f"# TrendMind Daily Digest — {digest_date.isoformat()}", ""]

    lines.append("## Top Stories")
    lines.append("")
    if top_stories:
        for article in top_stories:
            source_name = article.source.name if article.source else "Unknown source"
            summary = article.summary_short or "No summary available."
            lines.append(f"### [{article.title}]({article.url})")
            lines.append(
                f"*{source_name} — {article.category or 'Uncategorized'} — "
                f"{article.importance or 'Medium'} importance*"
            )
            lines.append("")
            lines.append(summary)
            lines.append("")
    else:
        lines.append("No qualifying stories were published in this window.")
        lines.append("")

    lines.append("## Trend Spotlight")
    lines.append("")
    if trend is not None:
        article_count = len(trend.articles) if trend.articles is not None else 0
        plural = "s" if article_count != 1 else ""
        lines.append(f"**{trend.title}**")
        lines.append("")
        lines.append(trend.description or "No description available.")
        lines.append("")
        lines.append(f"_Tracked across {article_count} article{plural}._")
    else:
        lines.append("No trend has been generated yet — run `POST /trends/generate` first.")

    return "\n".join(lines).strip() + "\n"


def generate_newsletter(
    db: Session,
    digest_date: date_type | None = None,
    lookback_days: int = 1,
    top_stories_limit: int = 5,
) -> tuple[NewsletterEntry, int, bool]:
    target_date = digest_date or datetime.now(timezone.utc).date()
    window_end = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    window_start = window_end - timedelta(days=lookback_days)

    top_stories = _get_top_stories(db, window_start, window_end, top_stories_limit)
    trend = _get_biggest_trend(db, window_start, window_end)
    content_markdown = _render_markdown(target_date, top_stories, trend)

    entry = db.query(NewsletterEntry).filter(NewsletterEntry.digest_date == target_date).first()
    if entry is None:
        entry = NewsletterEntry(digest_date=target_date, content_markdown=content_markdown)
        db.add(entry)
    else:
        entry.content_markdown = content_markdown

    db.commit()
    db.refresh(entry)

    logger.info(
        "Newsletter generated for %s: %d top stories, trend_included=%s",
        target_date, len(top_stories), trend is not None,
    )
    return entry, len(top_stories), trend is not None


def get_newsletter_by_date(db: Session, digest_date: date_type) -> NewsletterEntry | None:
    return db.query(NewsletterEntry).filter(NewsletterEntry.digest_date == digest_date).first()


def list_newsletters(
    db: Session, limit: int = 20, offset: int = 0
) -> tuple[list[NewsletterEntry], int]:
    query = db.query(NewsletterEntry).order_by(NewsletterEntry.digest_date.desc())
    total = query.order_by(None).count()
    items = query.limit(limit).offset(offset).all()
    return items, total
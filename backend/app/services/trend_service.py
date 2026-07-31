from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload

from app.agents.duplicate_agent import cosine_similarity
from app.agents.embedding_agent import get_embedding_function
from app.agents.llm_client import run_structured
from app.agents.prompts.trend_prompt import TREND_SYSTEM_PROMPT, TrendSummary, build_trend_prompt
from app.models.article import Article
from app.models.trend import Trend
from app.schemas.article import ArticleListItem
from app.schemas.trend import TrendDetail
from app.vectorstore.chroma_client import get_embeddings_by_ids, get_vectorstore


def _get_recent_clusterable_articles(db: Session, days: int) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(Article)
        .filter(Article.embedding_id.isnot(None))
        .filter(Article.duplicate_of_id.is_(None))  # trends are built over canonical articles only
        .filter(Article.published_at.isnot(None))
        .filter(Article.published_at >= cutoff)
        .all()
    )


def _cluster_articles(
    articles: list[Article],
    embeddings_by_article_id: dict[int, list[float]],
    similarity_threshold: float,
) -> list[list[Article]]:
    clusters: list[list[Article]] = []

    for article in articles:
        emb = embeddings_by_article_id.get(article.id)
        if emb is None:
            continue

        placed = False
        for cluster in clusters:
            if any(
                cosine_similarity(emb, embeddings_by_article_id[member.id]) >= similarity_threshold
                for member in cluster
                if member.id in embeddings_by_article_id
            ):
                cluster.append(article)
                placed = True
                break
        if not placed:
            clusters.append([article])

    return clusters


def _summarize_cluster(articles: list[Article]) -> TrendSummary:
    prompt_articles = [
        {"title": a.title, "summary_short": a.summary_short, "category": a.category}
        for a in articles
    ]
    prompt = f"{TREND_SYSTEM_PROMPT}\n\n{build_trend_prompt(prompt_articles)}"
    result, error = run_structured(prompt, TrendSummary)
    if result is not None:
        return result
    fallback_title = articles[0].title[:80]
    fallback_desc = (
        f"{len(articles)} related articles"
        + (f" (LLM summarization failed: {error.message})" if error else "")
    )
    return TrendSummary(title=fallback_title, description=fallback_desc)


def generate_trends(
    db: Session,
    days: int = 7,
    min_cluster_size: int = 2,
    similarity_threshold: float = 0.75,
) -> tuple[list[Trend], int, int]:
    articles = _get_recent_clusterable_articles(db, days)
    if not articles:
        return [], 0, 0

    embedding_ids = [a.embedding_id for a in articles]
    vectorstore = get_vectorstore(get_embedding_function())
    embeddings_by_chroma_id = get_embeddings_by_ids(vectorstore, embedding_ids)
    embeddings_by_article_id = {
        a.id: embeddings_by_chroma_id[a.embedding_id]
        for a in articles
        if a.embedding_id in embeddings_by_chroma_id
    }

    clusters = _cluster_articles(articles, embeddings_by_article_id, similarity_threshold)
    qualifying_clusters = [c for c in clusters if len(c) >= min_cluster_size]

    period_start = min(a.published_at for a in articles)
    period_end = max(a.published_at for a in articles)

    created_trends: list[Trend] = []
    for cluster in qualifying_clusters:
        summary = _summarize_cluster(cluster)
        trend = Trend(
            title=summary.title,
            description=summary.description,
            period_start=period_start,
            period_end=period_end,
        )
        trend.articles = cluster
        db.add(trend)
        created_trends.append(trend)

    db.commit()
    for t in created_trends:
        db.refresh(t)

    clustered_count = sum(len(c) for c in qualifying_clusters)
    return created_trends, len(articles), clustered_count


def trend_to_detail(trend: Trend) -> TrendDetail:
    return TrendDetail(
        id=trend.id,
        title=trend.title,
        description=trend.description,
        period_start=trend.period_start,
        period_end=trend.period_end,
        created_at=trend.created_at,
        article_count=len(trend.articles),
        articles=[ArticleListItem.from_orm_article(a) for a in trend.articles],
    )
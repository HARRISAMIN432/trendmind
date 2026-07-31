from __future__ import annotations
import logging
from collections import Counter
from typing import Sequence

from sqlalchemy.orm import Session, joinedload

from app.agents.embedding_agent import get_embedding_function
from app.models.article import Article
from app.schemas.article import ArticleListItem
from app.schemas.recommendation import RecommendationResponse, RecommendedArticle
from app.vectorstore.chroma_client import (
    get_embeddings_by_ids,
    get_vectorstore,
    query_similar_with_scores,
)

logger = logging.getLogger(__name__)

FETCH_MULTIPLIER = 3


def _get_read_articles(db: Session, read_urls: Sequence[str]) -> list[Article]:
    if not read_urls:
        return []
    return (
        db.query(Article)
        .filter(Article.url.in_(list(read_urls)))
        .filter(Article.embedding_id.isnot(None))
        .all()
    )


def _build_category_profile(articles: Sequence[Article]) -> Counter:
    return Counter(a.category for a in articles if a.category)


def _average_embedding(vectors: Sequence[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    length = len(vectors[0])
    sums = [0.0] * length
    for vec in vectors:
        if len(vec) != length:
            continue
        for i, value in enumerate(vec):
            sums[i] += value
    return [value / len(vectors) for value in sums]


def get_recommendations(
    db: Session,
    read_urls: Sequence[str],
    limit: int = 10,
    category_boost: float = 0.15,
) -> RecommendationResponse:
    read_articles = _get_read_articles(db, read_urls)
    category_profile = _build_category_profile(read_articles)

    if not read_articles:
        return RecommendationResponse(recommendations=[], profile_categories={}, read_count_used=0)

    profile_embedding: list[float] | None = None
    vectorstore = None
    try:
        vectorstore = get_vectorstore(get_embedding_function())
        # embedding_id is now only a *base* id - the actual Chroma vector for
        # each article lives under "{embedding_id}:summary" (plus :context /
        # :technical if present). The summary chunk is the best single
        # stand-in for "what this article is about", so that's what we pull
        # per read article to build the recommendation profile.
        summary_chunk_ids = [
            f"{a.embedding_id}:summary" for a in read_articles if a.embedding_id
        ]
        embeddings_by_id = get_embeddings_by_ids(vectorstore, summary_chunk_ids)
        profile_embedding = _average_embedding(list(embeddings_by_id.values()))
    except Exception as exc:  # pragma: no cover - defensive, mirrors llm_client's own boundary
        logger.warning("Recommendation embedding lookup failed: %s", exc)
        profile_embedding = None

    if profile_embedding is None or vectorstore is None:
        return RecommendationResponse(
            recommendations=[],
            profile_categories=dict(category_profile),
            read_count_used=len(read_articles),
        )

    read_url_set = set(read_urls)
    fetch_n = max(limit * FETCH_MULTIPLIER, limit + len(read_articles))

    try:
        hits = query_similar_with_scores(vectorstore, profile_embedding, n_results=fetch_n)
    except Exception as exc:  # pragma: no cover
        logger.warning("Recommendation similarity query failed: %s", exc)
        hits = []

    scores_by_url: dict[str, float] = {}
    candidate_urls: list[str] = []
    for hit in hits:
        metadata = hit.get("metadata") or {}
        url = metadata.get("url")
        if not url or url in read_url_set:
            continue
        score = hit.get("score") or 0.0
        if url not in scores_by_url:
            candidate_urls.append(url)
            scores_by_url[url] = score
        elif score > scores_by_url[url]:
            scores_by_url[url] = score

    if not candidate_urls:
        return RecommendationResponse(
            recommendations=[],
            profile_categories=dict(category_profile),
            read_count_used=len(read_articles),
        )

    candidate_articles = (
        db.query(Article)
        .options(joinedload(Article.source), joinedload(Article.companies))
        .filter(Article.url.in_(candidate_urls))
        .filter(Article.duplicate_of_id.is_(None))
        .all()
    )

    scored: list[RecommendedArticle] = []
    for article in candidate_articles:
        base_score = scores_by_url.get(article.url, 0.0)
        matched_category = bool(article.category and article.category in category_profile)
        score = base_score + (category_boost if matched_category else 0.0)
        scored.append(
            RecommendedArticle(
                article=ArticleListItem.from_orm_article(article),
                score=round(score, 4),
                matched_category=matched_category,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)

    return RecommendationResponse(
        recommendations=scored[:limit],
        profile_categories=dict(category_profile),
        read_count_used=len(read_articles),
    )
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
try:
    from app.agents.embedding_agent import EmbeddedArticle
except ImportError:  
    from dataclasses import dataclass as _dc, field as _field

    @_dc
    class EmbeddedArticle:  
        title: str
        url: str
        source_name: str
        published_at: Any
        raw_content: str
        clean_content: str
        category: str
        sub_category: str
        companies: list[str] = _field(default_factory=list)
        importance: str = "Medium"
        summary_short: str = ""
        key_takeaway: str = ""
        why_it_matters: str = ""
        technical_highlights: str = ""
        embedding_id: str = ""
        embedding: list[float] = _field(default_factory=list)

SIMILARITY_THRESHOLD = 0.92


@dataclass
class DeduplicatedArticle:
    title: str
    url: str
    source_name: str
    published_at: Any
    raw_content: str
    clean_content: str
    category: str
    sub_category: str
    companies: list[str]
    importance: str
    summary_short: str
    key_takeaway: str
    why_it_matters: str
    technical_highlights: str
    embedding_id: str
    embedding: list[float]
    is_duplicate: bool = False
    duplicate_of_url: str | None = None
    similarity_score: float | None = None

    @classmethod
    def from_embedded(
        cls,
        article: EmbeddedArticle,
        is_duplicate: bool = False,
        duplicate_of_url: str | None = None,
        similarity_score: float | None = None,
    ) -> "DeduplicatedArticle":
        return cls(
            **asdict(article),
            is_duplicate=is_duplicate,
            duplicate_of_url=duplicate_of_url,
            similarity_score=similarity_score,
        )


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sort_key(article: EmbeddedArticle):
    return (article.published_at is None, article.published_at)


def find_duplicates(
    articles: list[EmbeddedArticle],
    existing_articles: list[EmbeddedArticle] | None = None,
) -> list[DeduplicatedArticle]:
    existing_articles = existing_articles or []
    ordered = sorted(articles, key=_sort_key)

    canonical_pool: list[tuple[str, list[float]]] = [
        (a.url, a.embedding) for a in existing_articles
    ]

    results_by_url: dict[str, DeduplicatedArticle] = {}

    for article in ordered:
        best_url: str | None = None
        best_score = 0.0

        for candidate_url, candidate_embedding in canonical_pool:
            score = cosine_similarity(article.embedding, candidate_embedding)
            if score > best_score:
                best_score = score
                best_url = candidate_url

        if best_url is not None and best_score >= SIMILARITY_THRESHOLD:
            results_by_url[article.url] = DeduplicatedArticle.from_embedded(
                article,
                is_duplicate=True,
                duplicate_of_url=best_url,
                similarity_score=best_score,
            )
            
        else:
            results_by_url[article.url] = DeduplicatedArticle.from_embedded(
                article, is_duplicate=False
            )
            canonical_pool.append((article.url, article.embedding))

    return [results_by_url[a.url] for a in articles]


def duplicate_node(state: dict) -> dict:
    articles: list[EmbeddedArticle] = state.get("articles", [])
    existing = state.get("existing_embedded_articles")

    deduplicated = find_duplicates(articles, existing_articles=existing)

    state["articles"] = deduplicated
    state["duplicate_count"] = sum(1 for a in deduplicated if a.is_duplicate)
    return state
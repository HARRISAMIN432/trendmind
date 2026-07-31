from __future__ import annotations
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.agents.embedding_agent import get_embedding_function
from app.agents.llm_client import run_structured
from app.agents.prompts.chat_prompt import (
    REWRITE_SYSTEM_PROMPT,
    QueryRewrite,
    build_rewrite_prompt,
)
from app.models.article import Article
from app.vectorstore.chroma_client import get_vectorstore, query_similar_with_scores

logger = logging.getLogger("digestai.search")


@dataclass
class SearchHit:
    article: Article
    score: float

def _transform_query_if_needed(query: str) -> str:
    word_count = len([word for word in query.split() if word.strip()])
    
    if word_count < 7:
        transformed = f"What is the news about {query}"
        return transformed
    
    return query


def _rewrite_query_for_retrieval(query: str) -> str:
    """Expand a short/terse query into a richer one for embedding search.

    e.g. "gpt-5" -> "GPT-5 OpenAI ChatGPT large language model release"

    Only calls the LLM for queries under 5 words - longer queries skip the
    LLM entirely and go through the deterministic transform instead, to
    avoid the extra call/latency when the query already has enough words
    to work with.

    Fails open: on any LLM error, or an empty/degenerate result, falls back
    to the deterministic transform so retrieval never breaks because
    rewriting did.
    """
    word_count = len([w for w in query.split() if w.strip()])
    if word_count >= 5:
        return _transform_query_if_needed(query)

    prompt = build_rewrite_prompt(query=query)
    full_prompt = f"{REWRITE_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, QueryRewrite)

    if result is None or not result.rewritten_query.strip():
        logger.warning(
            "query rewrite failed%s, falling back to deterministic transform. query=%r",
            f" ({error.message})" if error else "",
            query,
        )
        return _transform_query_if_needed(query)

    rewritten = result.rewritten_query.strip()
    logger.info("query rewrite: %r -> %r", query, rewritten)
    return rewritten


def semantic_search(
    db: Session,
    query: str,
    n_results: int = 10,
    category: str | None = None,
    include_duplicates: bool = False,
    min_score: float = 0.3,
    rewrite_query: bool = True,
) -> list[SearchHit]:
    query = query.strip()
    if not query:
        return []

    retrieval_query = (
        _rewrite_query_for_retrieval(query)
        if rewrite_query
        else _transform_query_if_needed(query)
    )

    embedding_fn = get_embedding_function()
    vectorstore = get_vectorstore(embedding_fn)
    query_embedding = embedding_fn.embed_query(retrieval_query)

    where = {"category": category} if category else None

    raw_hits = query_similar_with_scores(
        vectorstore, query_embedding, n_results=n_results * 9, where=where
    )
    if not raw_hits:
        return []

    raw_hits = [h for h in raw_hits if (h["score"] or 0) > min_score]
    if not raw_hits:
        return []

    best_score_by_url: dict[str, float] = {}
    for hit in raw_hits:
        url = (hit.get("metadata") or {}).get("url")
        if not url:
            continue
        score = hit["score"] or 0.0
        if url not in best_score_by_url or score > best_score_by_url[url]:
            best_score_by_url[url] = score

    if not best_score_by_url:
        return []

    articles = (
        db.query(Article)
        .options(joinedload(Article.source), joinedload(Article.companies))
        .filter(Article.url.in_(best_score_by_url.keys()))
        .all()
    )
    articles_by_url = {a.url: a for a in articles}

    sorted_urls = sorted(best_score_by_url, key=lambda u: best_score_by_url[u], reverse=True)

    hits: list[SearchHit] = []
    for url in sorted_urls:
        article = articles_by_url.get(url)
        if article is None:
            continue
        if not include_duplicates and article.duplicate_of_id is not None:
            continue
        hits.append(SearchHit(article=article, score=best_score_by_url[url]))
        if len(hits) >= n_results:
            break

    return hits
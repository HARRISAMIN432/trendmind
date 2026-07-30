from __future__ import annotations
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.agents.embedding_agent import get_embedding_model
from app.models.article import Article
from app.vectorstore.chroma_client import get_vectorstore, query_similar_with_scores


@dataclass
class SearchHit:
    article: Article
    score: float


def semantic_search(
    db: Session,
    query: str,
    n_results: int = 10,
    category: str | None = None,
    include_duplicates: bool = False,
) -> list[SearchHit]:
    query = query.strip()
    if not query:
        return []

    model = get_embedding_model()
    vectorstore = get_vectorstore(model)
    query_embedding = model.embed_query(query)

    where = {"category": category} if category else None
    
    raw_hits = query_similar_with_scores(
        vectorstore, query_embedding, n_results=n_results * 3, where=where
    )
    if not raw_hits:
        return []

    ids = [hit["id"] for hit in raw_hits]
    score_by_id = {hit["id"]: hit["score"] for hit in raw_hits}

    articles = (
        db.query(Article)
        .options(joinedload(Article.source), joinedload(Article.companies))
        .filter(Article.embedding_id.in_(ids))
        .all()
    )
    articles_by_embedding_id = {a.embedding_id: a for a in articles}

    hits: list[SearchHit] = []
    for embedding_id in ids: 
        article = articles_by_embedding_id.get(embedding_id)
        if article is None:
            continue  
        if not include_duplicates and article.duplicate_of_id is not None:
            continue
        hits.append(SearchHit(article=article, score=score_by_id[embedding_id]))
        if len(hits) >= n_results:
            break

    return hits
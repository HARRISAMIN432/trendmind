from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchResponse, SearchResultItem
from app.schemas.article import ArticleListItem
from app.services.search_service import semantic_search
from app.api.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def search_articles(
    request: Request,
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    limit: int = Query(10, ge=1, le=50),
    category: str | None = Query(None),
    include_duplicates: bool = Query(False),
    db: Session = Depends(get_db),
) -> SearchResponse:
    hits = semantic_search(
        db=db, query=q, n_results=limit, category=category,
        include_duplicates=include_duplicates,
    )
    return SearchResponse(
        query=q,
        count=len(hits),
        results=[
            SearchResultItem(
                article=ArticleListItem.from_orm_article(hit.article),
                score=round(hit.score, 4),
            )
            for hit in hits
        ],
    )
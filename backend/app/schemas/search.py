from __future__ import annotations
from pydantic import BaseModel
from app.schemas.article import ArticleListItem


class SearchResultItem(BaseModel):
    article: ArticleListItem
    score: float


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResultItem]
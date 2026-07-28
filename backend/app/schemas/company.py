from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from app.schemas.article import ArticleListItem

class CompanyListItem(BaseModel):
    """GET /companies row shape - deliberately lightweight (no LLM call per row)."""

    id: int
    name: str
    article_count: int


class PaginatedCompanies(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CompanyListItem]


class CompanyProfile(BaseModel):
    """GET /companies/{name} shape - the LLM-synthesized profile plus deterministic
    aggregates computed directly from the article set (never LLM-derived)."""

    id: int
    name: str
    article_count: int
    first_mentioned_at: datetime | None
    last_mentioned_at: datetime | None
    category_breakdown: dict[str, int]
    overview: str
    timeline_highlights: list[str]
    products: list[str]
    funding_mentions: list[str]
    articles: list[ArticleListItem]
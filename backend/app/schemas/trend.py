from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.article import ArticleListItem


class TrendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    created_at: datetime
    article_count: int = 0


class TrendDetail(TrendRead):
    articles: list[ArticleListItem] = []


class PaginatedTrends(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TrendRead]


class TrendGenerateRequest(BaseModel):
    days: int = Field(7, ge=1, le=90, description="Look back this many days (by published_at).")
    min_cluster_size: int = Field(2, ge=2, description="Minimum articles required to form a trend.")
    similarity_threshold: float = Field(0.75, ge=0.0, le=1.0)


class TrendGenerateResponse(BaseModel):
    trends_created: int
    articles_considered: int
    articles_clustered: int
    trends: list[TrendDetail]
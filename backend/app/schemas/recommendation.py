from __future__ import annotations
from pydantic import BaseModel, Field
from app.schemas.article import ArticleListItem


class RecommendationRequest(BaseModel):
    read_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="URLs of articles the user has already read - used to build their interest profile.",
    )
    limit: int = Field(10, ge=1, le=50)
    category_boost: float = Field(
        0.15,
        ge=0.0,
        le=1.0,
        description="Score bonus applied to candidates whose category matches one the user has read before.",
    )


class RecommendedArticle(BaseModel):
    article: ArticleListItem
    score: float
    matched_category: bool


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendedArticle]
    profile_categories: dict[str, int]
    read_count_used: int
from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel, Field


class NewsletterEntryRead(BaseModel):
    id: int
    digest_date: date
    content_markdown: str
    created_at: datetime

    class Config:
        from_attributes = True


class NewsletterGenerateRequest(BaseModel):
    digest_date: date | None = Field(
        None, description="Defaults to today (UTC) if omitted."
    )
    lookback_days: int = Field(
        1, ge=1, le=30, description="How many days back from digest_date to pull top stories/trends from."
    )
    top_stories_limit: int = Field(5, ge=1, le=20)


class NewsletterGenerateResponse(BaseModel):
    entry: NewsletterEntryRead
    top_story_count: int
    trend_included: bool


class PaginatedNewsletterEntries(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[NewsletterEntryRead]
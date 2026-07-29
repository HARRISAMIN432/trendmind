from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.newsletter import (
    NewsletterEntryRead,
    NewsletterGenerateRequest,
    NewsletterGenerateResponse,
    PaginatedNewsletterEntries,
)
from app.services.newsletter_service import (
    generate_newsletter,
    get_newsletter_by_date,
    list_newsletters,
)
from app.api.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.get("", response_model=PaginatedNewsletterEntries)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_newsletters(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedNewsletterEntries:
    items, total = list_newsletters(db, limit=limit, offset=offset)
    return PaginatedNewsletterEntries(total=total, limit=limit, offset=offset, items=items)


@router.get("/{digest_date}", response_model=NewsletterEntryRead)
def get_newsletter(digest_date: date, db: Session = Depends(get_db)) -> NewsletterEntryRead:
    entry = get_newsletter_by_date(db, digest_date)
    if entry is None:
        raise HTTPException(
            status_code=404, detail=f"No newsletter found for {digest_date.isoformat()}"
        )
    return entry


@router.post("/generate", response_model=NewsletterGenerateResponse)
def generate(
    payload: NewsletterGenerateRequest, db: Session = Depends(get_db)
) -> NewsletterGenerateResponse:
    entry, top_story_count, trend_included = generate_newsletter(
        db,
        digest_date=payload.digest_date,
        lookback_days=payload.lookback_days,
        top_stories_limit=payload.top_stories_limit,
    )
    return NewsletterGenerateResponse(
        entry=entry, top_story_count=top_story_count, trend_included=trend_included
    )
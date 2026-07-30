from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.trend import Trend
from app.models.article import Article
from app.schemas.trend import (
    PaginatedTrends, TrendDetail, TrendGenerateRequest, TrendGenerateResponse, TrendRead,
)
from app.services.trend_service import generate_trends, trend_to_detail
from app.middleware.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("", response_model=PaginatedTrends)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def list_trends(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedTrends:
    query = db.query(Trend).options(joinedload(Trend.articles))
    total = query.count()
    trends = query.order_by(Trend.created_at.desc()).offset(offset).limit(limit).all()

    return PaginatedTrends(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            TrendRead(
                id=t.id, title=t.title, description=t.description,
                period_start=t.period_start, period_end=t.period_end,
                created_at=t.created_at, article_count=len(t.articles),
            )
            for t in trends
        ],
    )


@router.get("/{trend_id}", response_model=TrendDetail)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_trend(request, Request, trend_id: int, db: Session = Depends(get_db)) -> TrendDetail:
    trend = (
        db.query(Trend)
        .options(joinedload(Trend.articles).joinedload(Article.source), joinedload(Trend.articles).joinedload(Article.companies))
        .filter(Trend.id == trend_id)
        .first()
    )
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    return trend_to_detail(trend)


@router.post("/generate", response_model=TrendGenerateResponse)
def generate_trends_endpoint(
    payload: TrendGenerateRequest,
    db: Session = Depends(get_db),
) -> TrendGenerateResponse:
    trends, considered, clustered = generate_trends(
        db=db,
        days=payload.days,
        min_cluster_size=payload.min_cluster_size,
        similarity_threshold=payload.similarity_threshold,
    )
    return TrendGenerateResponse(
        trends_created=len(trends),
        articles_considered=considered,
        articles_clustered=clustered,
        trends=[trend_to_detail(t) for t in trends],
    )
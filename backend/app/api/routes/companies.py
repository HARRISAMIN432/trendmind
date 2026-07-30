from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.company import CompanyProfile, PaginatedCompanies
from app.services.company_service import generate_company_profile, list_companies
from app.middleware.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=PaginatedCompanies)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_companies(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedCompanies:
    items, total = list_companies(db, limit=limit, offset=offset)
    return PaginatedCompanies(total=total, limit=limit, offset=offset, items=items)


@router.get("/{company_name}", response_model=CompanyProfile)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_company_profile(
    request: Request,
    company_name: str,
    include_duplicates: bool = Query(False),
    db: Session = Depends(get_db),
) -> CompanyProfile:
    profile = generate_company_profile(db, company_name, include_duplicates=include_duplicates)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")
    return profile
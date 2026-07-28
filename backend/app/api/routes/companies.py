from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.company import CompanyProfile, PaginatedCompanies
from app.services.company_service import generate_company_profile, list_companies

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=PaginatedCompanies)
def get_companies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedCompanies:
    items, total = list_companies(db, limit=limit, offset=offset)
    return PaginatedCompanies(total=total, limit=limit, offset=offset, items=items)


@router.get("/{company_name}", response_model=CompanyProfile)
def get_company_profile(
    company_name: str,
    include_duplicates: bool = Query(False),
    db: Session = Depends(get_db),
) -> CompanyProfile:
    profile = generate_company_profile(db, company_name, include_duplicates=include_duplicates)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found")
    return profile
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.article import Article
from app.models.company import Company
from app.schemas.article import (
    ArticleListItem, ArticleDetail, ArticleCreate, ArticleUpdate, PaginatedArticles,
)

router = APIRouter(prefix="/articles", tags=["articles"])


def _base_query(db: Session):
    return db.query(Article).options(
        joinedload(Article.source), joinedload(Article.companies)
    )


@router.get("", response_model=PaginatedArticles)
def list_articles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    sub_category: str | None = None,
    importance: str | None = None,
    source_id: int | None = None,
    company: str | None = Query(None, description="Exact, case-insensitive company name"),
    search: str | None = Query(None, description="Case-insensitive title search"),
    include_duplicates: bool = Query(False),
    sort_by: str = Query("published_at", pattern="^(published_at|created_at)$"),
    db: Session = Depends(get_db),
) -> PaginatedArticles:
    query = _base_query(db)

    if category:
        query = query.filter(Article.category == category)
    if sub_category:
        query = query.filter(Article.sub_category == sub_category)
    if importance:
        query = query.filter(Article.importance == importance)
    if source_id is not None:
        query = query.filter(Article.source_id == source_id)
    if company:
        query = query.join(Article.companies).filter(Company.name.ilike(company))
    if search:
        query = query.filter(Article.title.ilike(f"%{search}%"))
    if not include_duplicates:
        query = query.filter(Article.duplicate_of_id.is_(None))
    if company:
        query = query.distinct()

    total = query.order_by(None).count()

    sort_col = Article.published_at if sort_by == "published_at" else Article.created_at
    query = query.order_by(sort_col.desc().nullslast())

    articles = query.offset(offset).limit(limit).all()

    return PaginatedArticles(
        total=total,
        limit=limit,
        offset=offset,
        items=[ArticleListItem.from_orm_article(a) for a in articles],
    )


@router.get("/{article_id}", response_model=ArticleDetail)
def get_article(article_id: int, db: Session = Depends(get_db)) -> ArticleDetail:
    article = _base_query(db).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetail.from_orm_article(article)


def _resolve_companies(db: Session, names: list[str]) -> list[Company]:
    companies = []
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        company = db.query(Company).filter(Company.name.ilike(name)).first()
        if company is None:
            company = Company(name=name)
            db.add(company)
            db.flush()
        companies.append(company)
    return companies


@router.post("", response_model=ArticleDetail, status_code=201)
def create_article(payload: ArticleCreate, db: Session = Depends(get_db)) -> ArticleDetail:
    existing = db.query(Article).filter(Article.url == payload.url).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Article with this URL already exists")

    data = payload.model_dump(exclude={"company_names"})
    article = Article(**data)
    article.companies = _resolve_companies(db, payload.company_names)

    db.add(article)
    db.commit()
    db.refresh(article)
    return ArticleDetail.from_orm_article(article)


@router.patch("/{article_id}", response_model=ArticleDetail)
def update_article(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db)) -> ArticleDetail:
    article = _base_query(db).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = payload.model_dump(exclude_unset=True, exclude={"company_names"})
    for field, value in update_data.items():
        setattr(article, field, value)

    if payload.company_names is not None:
        article.companies = _resolve_companies(db, payload.company_names)

    db.commit()
    db.refresh(article)
    return ArticleDetail.from_orm_article(article)


@router.delete("/{article_id}", status_code=204, response_model=None)
def delete_article(article_id: int, db: Session = Depends(get_db)) -> None:
    article = db.query(Article).filter(Article.id == article_id).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
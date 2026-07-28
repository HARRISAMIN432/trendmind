from __future__ import annotations
from collections import Counter

from sqlalchemy.orm import Session, joinedload

from app.agents.llm_client import run_structured
from app.agents.prompts.company_prompt import (
    COMPANY_SYSTEM_PROMPT,
    CompanyProfileSummary,
    build_company_prompt,
)
from app.models.article import Article
from app.models.company import Company
from app.schemas.article import ArticleListItem
from app.schemas.company import CompanyListItem, CompanyProfile


def get_company_by_name(db: Session, name: str) -> Company | None:
    """Case-insensitive exact match, same convention as M09's `company` filter on
    GET /articles (ilike with no wildcards, not substring)."""
    return db.query(Company).filter(Company.name.ilike(name)).first()


def _get_company_articles(
    db: Session, company: Company, include_duplicates: bool = False
) -> list[Article]:
    query = (
        db.query(Article)
        .join(Article.companies)
        .filter(Company.id == company.id)
        .options(joinedload(Article.source), joinedload(Article.companies))
    )
    if not include_duplicates:
        # Same M07 "flag not filter" contract enforced at this boundary as M09/M12 already do.
        query = query.filter(Article.duplicate_of_id.is_(None))
    return query.order_by(Article.published_at.asc()).all()


def list_companies(
    db: Session, limit: int = 50, offset: int = 0
) -> tuple[list[CompanyListItem], int]:
    """
    Lists every tracked Company with its canonical (non-duplicate) article count,
    sorted by article_count desc. Companies with zero qualifying articles are still
    included - absence of coverage is itself informative for a "which companies are
    we tracking" view, not something worth hiding.

    Note: this issues one count() query per company (not a single GROUP BY), which is
    fine at portfolio scale (tens of companies) but would need a real aggregate query
    if the companies table grows into the hundreds.
    """
    companies = db.query(Company).all()
    items: list[CompanyListItem] = []
    for company in companies:
        count = (
            db.query(Article)
            .join(Article.companies)
            .filter(Company.id == company.id)
            .filter(Article.duplicate_of_id.is_(None))
            .count()
        )
        items.append(CompanyListItem(id=company.id, name=company.name, article_count=count))

    items.sort(key=lambda c: c.article_count, reverse=True)
    total = len(items)
    return items[offset : offset + limit], total


def _build_profile_summary(company_name: str, articles: list[Article]) -> CompanyProfileSummary:
    prompt_articles = [
        {
            "title": a.title,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "category": a.category,
            "summary_short": a.summary_short,
        }
        for a in articles
    ]
    prompt = f"{COMPANY_SYSTEM_PROMPT}\n\n{build_company_prompt(company_name, prompt_articles)}"
    result, error = run_structured(prompt, CompanyProfileSummary)
    if result is not None:
        return result

    # Fail-soft on LLM failure, same pattern as M11's chat path and M12's trend
    # summarization: never drop the request, degrade to a plain-language fallback.
    fallback_overview = (
        f"{len(articles)} articles mention {company_name}."
        + (f" (LLM synthesis failed: {error.message})" if error else "")
    )
    return CompanyProfileSummary(
        overview=fallback_overview, timeline_highlights=[], products=[], funding_mentions=[]
    )


def generate_company_profile(
    db: Session, company_name: str, include_duplicates: bool = False
) -> CompanyProfile | None:
    """Returns None if no Company row matches `company_name` - caller (the route) turns
    that into a 404. Deterministic aggregates (article_count, first/last mentioned,
    category_breakdown) are computed directly from the article set, never from the LLM -
    only the free-text narrative fields (overview/timeline/products/funding) come from
    run_structured."""
    company = get_company_by_name(db, company_name)
    if company is None:
        return None

    articles = _get_company_articles(db, company, include_duplicates=include_duplicates)
    if not articles:
        return CompanyProfile(
            id=company.id,
            name=company.name,
            article_count=0,
            first_mentioned_at=None,
            last_mentioned_at=None,
            category_breakdown={},
            overview=f"No tracked articles currently mention {company.name}.",
            timeline_highlights=[],
            products=[],
            funding_mentions=[],
            articles=[],
        )

    summary = _build_profile_summary(company.name, articles)
    category_breakdown = dict(Counter(a.category for a in articles if a.category))
    dated = [a.published_at for a in articles if a.published_at is not None]

    return CompanyProfile(
        id=company.id,
        name=company.name,
        article_count=len(articles),
        first_mentioned_at=min(dated) if dated else None,
        last_mentioned_at=max(dated) if dated else None,
        category_breakdown=category_breakdown,
        overview=summary.overview,
        timeline_highlights=summary.timeline_highlights,
        products=summary.products,
        funding_mentions=summary.funding_mentions,
        articles=[ArticleListItem.from_orm_article(a) for a in articles],
    )
from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.article import Article
from app.models.company import Company
from app.agents.llm_client import LLMCallError
from app.agents.prompts.company_prompt import CompanyProfileSummary
from app.services import company_service


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_article(title, published_at, category="Research", summary_short="summary", duplicate_of_id=None):
    return Article(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        published_at=published_at,
        category=category,
        summary_short=summary_short,
        duplicate_of_id=duplicate_of_id,
    )


def test_generate_company_profile_returns_none_when_company_not_found(db_session):
    assert company_service.generate_company_profile(db_session, "Nonexistent Inc") is None


def test_generate_company_profile_no_articles_skips_llm_call(db_session):
    company = Company(name="EmptyCo")
    db_session.add(company)
    db_session.commit()

    with patch("app.services.company_service.run_structured") as mock_run:
        profile = company_service.generate_company_profile(db_session, "EmptyCo")

    mock_run.assert_not_called()
    assert profile is not None
    assert profile.article_count == 0
    assert profile.overview.startswith("No tracked articles")


def test_generate_company_profile_aggregates_and_calls_llm(db_session):
    company = Company(name="Acme AI")
    a1 = _make_article("Acme raises funding", datetime(2026, 1, 1, tzinfo=timezone.utc))
    a2 = _make_article("Acme ships new model", datetime(2026, 2, 1, tzinfo=timezone.utc))
    a1.companies = [company]
    a2.companies = [company]
    db_session.add_all([company, a1, a2])
    db_session.commit()

    fake_summary = CompanyProfileSummary(
        overview="Acme AI raised funding and shipped a model.",
        timeline_highlights=["Jan 2026: raised funding", "Feb 2026: shipped model"],
        products=["Acme Model 1"],
        funding_mentions=["Undisclosed round in Jan 2026"],
    )
    with patch("app.services.company_service.run_structured", return_value=(fake_summary, None)):
        # case-insensitive lookup, same convention as M09's company filter
        profile = company_service.generate_company_profile(db_session, "acme ai")

    assert profile.article_count == 2
    # SQLite's DateTime(timezone=True) columns round-trip as naive datetimes (Postgres/
    # Neon would preserve tzinfo correctly) - strip tzinfo before comparing so this test
    # isn't asserting a SQLite-only artifact rather than the service's actual behavior.
    assert profile.first_mentioned_at.replace(tzinfo=None) == datetime(2026, 1, 1)
    assert profile.last_mentioned_at.replace(tzinfo=None) == datetime(2026, 2, 1)
    assert profile.category_breakdown == {"Research": 2}
    assert profile.overview == fake_summary.overview
    assert profile.products == ["Acme Model 1"]
    assert len(profile.articles) == 2


def test_generate_company_profile_excludes_duplicates_by_default(db_session):
    company = Company(name="DupCo")
    canonical = _make_article("Original story", datetime(2026, 1, 1, tzinfo=timezone.utc))
    db_session.add_all([company, canonical])
    db_session.commit()

    duplicate = _make_article(
        "Same story elsewhere",
        datetime(2026, 1, 2, tzinfo=timezone.utc),
        duplicate_of_id=canonical.id,
    )
    db_session.add(duplicate)
    duplicate.companies = [company]
    canonical.companies = [company]
    db_session.commit()

    with patch("app.services.company_service.run_structured", return_value=(None, None)):
        profile = company_service.generate_company_profile(db_session, "DupCo")

    assert profile.article_count == 1


def test_generate_company_profile_includes_duplicates_when_requested(db_session):
    company = Company(name="DupCo2")
    canonical = _make_article("Original story 2", datetime(2026, 1, 1, tzinfo=timezone.utc))
    db_session.add_all([company, canonical])
    db_session.commit()

    duplicate = _make_article(
        "Same story elsewhere 2",
        datetime(2026, 1, 2, tzinfo=timezone.utc),
        duplicate_of_id=canonical.id,
    )
    db_session.add(duplicate)
    duplicate.companies = [company]
    canonical.companies = [company]
    db_session.commit()

    with patch("app.services.company_service.run_structured", return_value=(None, None)):
        profile = company_service.generate_company_profile(
            db_session, "DupCo2", include_duplicates=True
        )

    assert profile.article_count == 2


def test_generate_company_profile_fails_soft_on_llm_error(db_session):
    company = Company(name="FailCo")
    a1 = _make_article("Some story", datetime(2026, 1, 1, tzinfo=timezone.utc))
    a1.companies = [company]
    db_session.add_all([company, a1])
    db_session.commit()

    with patch(
        "app.services.company_service.run_structured",
        return_value=(None, LLMCallError(stage="no_provider", message="both providers down")),
    ):
        profile = company_service.generate_company_profile(db_session, "FailCo")

    assert "LLM synthesis failed" in profile.overview
    assert "both providers down" in profile.overview
    assert profile.products == []
    assert profile.timeline_highlights == []


def test_list_companies_sorted_by_article_count_desc(db_session):
    big = Company(name="BigCo")
    small = Company(name="SmallCo")
    a1 = _make_article("Big story 1", datetime(2026, 1, 1, tzinfo=timezone.utc))
    a2 = _make_article("Big story 2", datetime(2026, 1, 2, tzinfo=timezone.utc))
    a1.companies = [big]
    a2.companies = [big]
    db_session.add_all([big, small, a1, a2])
    db_session.commit()

    items, total = company_service.list_companies(db_session)

    assert total == 2
    assert items[0].name == "BigCo"
    assert items[0].article_count == 2
    assert items[1].name == "SmallCo"
    assert items[1].article_count == 0


def test_list_companies_respects_pagination(db_session):
    for i in range(5):
        db_session.add(Company(name=f"Company {i}"))
    db_session.commit()

    items, total = company_service.list_companies(db_session, limit=2, offset=2)

    assert total == 5
    assert len(items) == 2
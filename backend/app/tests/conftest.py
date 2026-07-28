from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db

from app.models import article, company, source, trend, newsletterentry, associations  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_article(db_session):
    """Factory fixture: make_article(title="...", url="...", **overrides) -> Article (committed)."""
    from app.models.article import Article

    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        defaults = {
            "title": f"Test Article {counter['n']}",
            "url": f"https://example.com/article-{counter['n']}",
        }
        defaults.update(overrides)
        a = Article(**defaults)
        db_session.add(a)
        db_session.commit()
        db_session.refresh(a)
        return a

    return _make


@pytest.fixture()
def make_company(db_session):
    from app.models.company import Company

    def _make(name: str):
        existing = db_session.query(Company).filter(Company.name == name).first()
        if existing:
            return existing
        c = Company(name=name)
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    return _make


@pytest.fixture()
def make_source(db_session):
    from app.models.source import Source

    def _make(**overrides):
        defaults = {"name": "Test Source", "rss_url": "https://example.com/feed"}
        defaults.update(overrides)
        s = Source(**defaults)
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)
        return s

    return _make
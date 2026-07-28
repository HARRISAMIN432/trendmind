from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.article import Article
from app.agents.entity_extraction_agent import EntityExtractionError
from app.agents.prompts.entity_prompt import (
    EntityExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
)
from app.services import graph_service


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_article(url_hint: str, days_old: int = 0):
    return Article(
        title=f"Article {url_hint}",
        url=f"https://example.com/{url_hint}",
        published_at=datetime.now(timezone.utc),
        clean_content="Acme AI released AcmeGPT today.",
        duplicate_of_id=None,
    )


def test_build_graph_creates_nodes_and_edges(db_session):
    article = _make_article("a1")
    db_session.add(article)
    db_session.commit()

    fake_result = EntityExtractionResult(
        entities=[
            ExtractedEntity(name="Acme AI", type="Company"),
            ExtractedEntity(name="AcmeGPT", type="Model"),
        ],
        relationships=[
            ExtractedRelationship(source="Acme AI", target="AcmeGPT", relation="released")
        ],
    )
    with patch("app.services.graph_service.extract_entities", return_value=(fake_result, None)):
        articles_processed, nodes_created, edges_created, errors = graph_service.build_graph(
            db_session, days=30
        )

    assert articles_processed == 1
    assert nodes_created == 2
    assert edges_created == 1
    assert errors == []

    graph = graph_service.get_graph(db_session)
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].relation == "released"


def test_build_graph_dedupes_nodes_and_edges_across_articles(db_session):
    a1 = _make_article("a1")
    a2 = _make_article("a2")
    db_session.add_all([a1, a2])
    db_session.commit()

    fake_result = EntityExtractionResult(
        entities=[
            ExtractedEntity(name="Acme AI", type="Company"),
            ExtractedEntity(name="AcmeGPT", type="Model"),
        ],
        relationships=[
            ExtractedRelationship(source="Acme AI", target="AcmeGPT", relation="released")
        ],
    )
    with patch("app.services.graph_service.extract_entities", return_value=(fake_result, None)):
        graph_service.build_graph(db_session, days=30)

    graph = graph_service.get_graph(db_session)
    # Same two entities mentioned identically in both articles collapse into one node
    # each (case-insensitive name+type dedup key), and the identical relationship
    # collapses into one edge, not two.
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1


def test_build_graph_dedupes_case_insensitively(db_session):
    a1 = _make_article("a1")
    db_session.add(a1)
    db_session.commit()

    result1 = EntityExtractionResult(
        entities=[ExtractedEntity(name="Acme AI", type="Company")], relationships=[]
    )
    with patch("app.services.graph_service.extract_entities", return_value=(result1, None)):
        graph_service.build_graph(db_session, days=30)

    a2 = _make_article("a2")
    db_session.add(a2)
    db_session.commit()

    result2 = EntityExtractionResult(
        entities=[ExtractedEntity(name="acme ai", type="Company")], relationships=[]
    )
    with patch("app.services.graph_service.extract_entities", return_value=(result2, None)):
        graph_service.build_graph(db_session, days=30)

    graph = graph_service.get_graph(db_session)
    assert len(graph.nodes) == 1


def test_build_graph_skips_relationship_referencing_unknown_entity(db_session):
    article = _make_article("a1")
    db_session.add(article)
    db_session.commit()

    fake_result = EntityExtractionResult(
        entities=[ExtractedEntity(name="Acme AI", type="Company")],
        relationships=[
            ExtractedRelationship(source="Acme AI", target="Ghost Entity", relation="acquired")
        ],
    )
    with patch("app.services.graph_service.extract_entities", return_value=(fake_result, None)):
        articles_processed, nodes_created, edges_created, errors = graph_service.build_graph(
            db_session, days=30
        )

    assert nodes_created == 1
    assert edges_created == 0  # relationship referencing a name not in `entities` is skipped
    assert errors == []


def test_build_graph_isolates_per_article_extraction_errors(db_session):
    article = _make_article("a1")
    db_session.add(article)
    db_session.commit()

    with patch(
        "app.services.graph_service.extract_entities",
        return_value=(None, EntityExtractionError(article_id=article.id, reason="empty clean_content")),
    ):
        articles_processed, nodes_created, edges_created, errors = graph_service.build_graph(
            db_session, days=30
        )

    assert articles_processed == 1
    assert nodes_created == 0
    assert edges_created == 0
    assert len(errors) == 1
    assert "empty clean_content" in errors[0]


def test_build_graph_excludes_duplicate_articles(db_session):
    canonical = _make_article("a1")
    db_session.add(canonical)
    db_session.commit()

    duplicate = _make_article("a2")
    duplicate.duplicate_of_id = canonical.id
    db_session.add(duplicate)
    db_session.commit()

    with patch("app.services.graph_service.extract_entities") as mock_extract:
        mock_extract.return_value = (
            EntityExtractionResult(entities=[], relationships=[]),
            None,
        )
        articles_processed, *_ = graph_service.build_graph(db_session, days=30)

    assert articles_processed == 1  # duplicate excluded, same M07 contract as M12/M13


def test_get_graph_empty(db_session):
    graph = graph_service.get_graph(db_session)
    assert graph.nodes == []
    assert graph.edges == []
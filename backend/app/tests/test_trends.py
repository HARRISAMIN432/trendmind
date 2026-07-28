"""
Tests for M12 - Trend Analysis API.

Mocks app.services.trend_service.cosine_similarity's inputs indirectly by
mocking get_embeddings_by_ids (so real vectors never need to be computed) and
run_structured (no live LLM call). Same call-site mocking pattern as
M04/M05/M10/M11's suites.

Run with: pytest backend/tests/test_trends_api.py -v
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.agents.llm_client import LLMCallError
from app.agents.prompts.trend_prompt import TrendSummary
from app.services.trend_service import generate_trends, trend_to_detail


NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def _stub_embedding_model_and_vectorstore():
    """
    generate_trends() calls get_vectorstore(get_embedding_model()) before
    get_embeddings_by_ids() ever runs - without stubbing these too, tests hang
    on the real sentence-transformers model load/download. Autoused so every
    test in this file gets this for free without repeating it in each patch block.
    """
    with patch("app.services.trend_service.get_embedding_model", return_value=MagicMock()), \
         patch("app.services.trend_service.get_vectorstore", return_value=MagicMock()):
        yield


def _recent_article(make_article, **overrides):
    defaults = {
        "published_at": NOW - timedelta(days=1),
        "duplicate_of_id": None,
    }
    defaults.update(overrides)
    return make_article(**defaults)


class TestGenerateTrends:
    def test_no_candidate_articles_returns_empty(self, db_session):
        with patch("app.services.trend_service.get_embeddings_by_ids", return_value={}):
            trends, considered, clustered = generate_trends(db_session)
        assert trends == []
        assert considered == 0
        assert clustered == 0

    def test_articles_without_embedding_id_excluded_from_candidates(self, db_session, make_article):
        _recent_article(make_article, title="No embedding", embedding_id=None)

        with patch("app.services.trend_service.get_embeddings_by_ids", return_value={}):
            trends, considered, clustered = generate_trends(db_session)
        assert considered == 0

    def test_duplicate_articles_excluded_from_candidates(self, db_session, make_article):
        canonical = _recent_article(make_article, title="Canonical", embedding_id="emb-1")
        _recent_article(make_article, title="Dupe", embedding_id="emb-2", duplicate_of_id=canonical.id)

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get:
            mock_get.return_value = {"emb-1": [1.0, 0.0]}
            trends, considered, clustered = generate_trends(db_session)
        assert considered == 1  # only the canonical article is a candidate

    def test_articles_outside_lookback_window_excluded(self, db_session, make_article):
        make_article(title="Old", published_at=NOW - timedelta(days=30), embedding_id="emb-1")

        with patch("app.services.trend_service.get_embeddings_by_ids", return_value={}):
            trends, considered, clustered = generate_trends(db_session, days=7)
        assert considered == 0

    def test_similar_articles_cluster_and_create_trend(self, db_session, make_article):
        a1 = _recent_article(make_article, title="OpenAI news A", embedding_id="emb-1", summary_short="s1")
        a2 = _recent_article(make_article, title="OpenAI news B", embedding_id="emb-2", summary_short="s2")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get, \
             patch("app.services.trend_service.cosine_similarity", return_value=0.95), \
             patch("app.services.trend_service.run_structured") as mock_run:
            mock_get.return_value = {"emb-1": [1.0, 0.0], "emb-2": [1.0, 0.0]}
            mock_run.return_value = (TrendSummary(title="OpenAI trend", description="Two related stories."), None)

            trends, considered, clustered = generate_trends(db_session, min_cluster_size=2)

        assert considered == 2
        assert clustered == 2
        assert len(trends) == 1
        assert trends[0].title == "OpenAI trend"
        assert len(trends[0].articles) == 2

    def test_dissimilar_articles_do_not_cluster(self, db_session, make_article):
        _recent_article(make_article, title="Story A", embedding_id="emb-1")
        _recent_article(make_article, title="Story B", embedding_id="emb-2")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get, \
             patch("app.services.trend_service.cosine_similarity", return_value=0.1):
            mock_get.return_value = {"emb-1": [1.0, 0.0], "emb-2": [0.0, 1.0]}
            trends, considered, clustered = generate_trends(db_session, min_cluster_size=2)

        assert considered == 2
        assert clustered == 0
        assert trends == []

    def test_clusters_below_min_size_are_not_promoted_to_trends(self, db_session, make_article):
        _recent_article(make_article, title="Lone article", embedding_id="emb-1")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get:
            mock_get.return_value = {"emb-1": [1.0, 0.0]}
            trends, considered, clustered = generate_trends(db_session, min_cluster_size=2)

        assert considered == 1
        assert clustered == 0
        assert trends == []

    def test_article_missing_from_chroma_fetch_is_skipped_not_crashed(self, db_session, make_article):
        _recent_article(make_article, title="Has vector", embedding_id="emb-1")
        _recent_article(make_article, title="Missing vector", embedding_id="emb-missing")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get:
            mock_get.return_value = {"emb-1": [1.0, 0.0]}  # emb-missing absent
            trends, considered, clustered = generate_trends(db_session, min_cluster_size=2)

        # Both count as "considered" (they passed the DB filter), but only one
        # had a usable embedding, so no cluster reaches min_cluster_size.
        assert considered == 2
        assert clustered == 0

    def test_llm_failure_falls_back_to_generic_trend_not_raise(self, db_session, make_article):
        a1 = _recent_article(make_article, title="Fallback source article", embedding_id="emb-1")
        a2 = _recent_article(make_article, title="Other article", embedding_id="emb-2")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get, \
             patch("app.services.trend_service.cosine_similarity", return_value=0.9), \
             patch("app.services.trend_service.run_structured") as mock_run:
            mock_get.return_value = {"emb-1": [1.0, 0.0], "emb-2": [1.0, 0.0]}
            mock_run.return_value = (None, LLMCallError(stage="no_provider", message="no keys set"))

            trends, considered, clustered = generate_trends(db_session, min_cluster_size=2)

        assert len(trends) == 1
        assert "Fallback source article"[:80] == trends[0].title
        assert "LLM summarization failed" in trends[0].description
        assert "no keys set" in trends[0].description


class TestTrendToDetail:
    def test_computes_article_count(self, db_session, make_article):
        from app.models.trend import Trend
        a1 = make_article(title="A")
        a2 = make_article(title="B")
        trend = Trend(title="T", description="D")
        trend.articles = [a1, a2]
        db_session.add(trend)
        db_session.commit()
        db_session.refresh(trend)

        detail = trend_to_detail(trend)
        assert detail.article_count == 2
        assert len(detail.articles) == 2


class TestTrendsEndpoints:
    def test_list_trends_empty(self, client):
        resp = client.get("/trends")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_trend_404(self, client):
        resp = client.get("/trends/999999")
        assert resp.status_code == 404

    def test_generate_trends_endpoint(self, client, make_article):
        a1 = _recent_article(make_article, title="Trend source A", embedding_id="emb-1")
        a2 = _recent_article(make_article, title="Trend source B", embedding_id="emb-2")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get, \
             patch("app.services.trend_service.cosine_similarity", return_value=0.9), \
             patch("app.services.trend_service.run_structured") as mock_run:
            mock_get.return_value = {"emb-1": [1.0, 0.0], "emb-2": [1.0, 0.0]}
            mock_run.return_value = (TrendSummary(title="Generated trend", description="desc"), None)

            resp = client.post("/trends/generate", json={"min_cluster_size": 2})

        assert resp.status_code == 200
        body = resp.json()
        assert body["trends_created"] == 1
        assert body["articles_considered"] == 2
        assert body["articles_clustered"] == 2
        assert body["trends"][0]["title"] == "Generated trend"

    def test_generate_trends_then_list_and_get(self, client, make_article):
        a1 = _recent_article(make_article, title="Persisted A", embedding_id="emb-1")
        a2 = _recent_article(make_article, title="Persisted B", embedding_id="emb-2")

        with patch("app.services.trend_service.get_embeddings_by_ids") as mock_get, \
             patch("app.services.trend_service.cosine_similarity", return_value=0.9), \
             patch("app.services.trend_service.run_structured") as mock_run:
            mock_get.return_value = {"emb-1": [1.0, 0.0], "emb-2": [1.0, 0.0]}
            mock_run.return_value = (TrendSummary(title="Persisted trend", description="desc"), None)

            gen_resp = client.post("/trends/generate", json={"min_cluster_size": 2})

        trend_id = gen_resp.json()["trends"][0]["id"]

        list_resp = client.get("/trends")
        assert list_resp.json()["total"] == 1

        detail_resp = client.get(f"/trends/{trend_id}")
        assert detail_resp.status_code == 200
        assert len(detail_resp.json()["articles"]) == 2

    def test_generate_trends_request_validation(self, client):
        resp = client.post("/trends/generate", json={"days": 0})
        assert resp.status_code == 422

        resp2 = client.post("/trends/generate", json={"min_cluster_size": 1})
        assert resp2.status_code == 422

        resp3 = client.post("/trends/generate", json={"similarity_threshold": 1.5})
        assert resp3.status_code == 422
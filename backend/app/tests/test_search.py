from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest
from app.services.search_service import semantic_search

def _fake_embedding_model():
    model = MagicMock()
    model.embed_query.return_value = [0.1, 0.2, 0.3]
    return model


def _chroma_hit(embedding_id: str, score: float):
    return {
        "id": embedding_id,
        "document": "doc text",
        "metadata": {},
        "distance": 1.0 - score,
        "score": score,
    }


class TestSemanticSearchService:
    def test_empty_query_returns_no_hits(self, db_session):
        hits = semantic_search(db_session, "   ")
        assert hits == []

    def test_returns_hits_matching_db_articles(self, db_session, make_article):
        a1 = make_article(title="First", embedding_id="emb-1")
        a2 = make_article(title="Second", embedding_id="emb-2")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [
                _chroma_hit("emb-1", 0.95),
                _chroma_hit("emb-2", 0.80),
            ]
            hits = semantic_search(db_session, "AI news")

        assert [h.article.id for h in hits] == [a1.id, a2.id]
        assert hits[0].score == pytest.approx(0.95)
        assert hits[1].score == pytest.approx(0.80)

    def test_preserves_chroma_relevance_order_not_db_order(self, db_session, make_article):
        # DB insertion order is a1, a2 but Chroma ranks a2 higher - result order
        # must follow Chroma's ranking, not the SQL IN(...) row order.
        a1 = make_article(title="First", embedding_id="emb-1")
        a2 = make_article(title="Second", embedding_id="emb-2")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [
                _chroma_hit("emb-2", 0.99),
                _chroma_hit("emb-1", 0.50),
            ]
            hits = semantic_search(db_session, "AI news")

        assert [h.article.id for h in hits] == [a2.id, a1.id]

    def test_skips_stale_chroma_id_with_no_db_row(self, db_session, make_article):
        make_article(title="Real article", embedding_id="emb-real")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [
                _chroma_hit("emb-ghost", 0.99),   # no matching Article row
                _chroma_hit("emb-real", 0.70),
            ]
            hits = semantic_search(db_session, "AI news")

        assert len(hits) == 1
        assert hits[0].article.embedding_id == "emb-real"

    def test_excludes_duplicates_by_default(self, db_session, make_article):
        canonical = make_article(title="Canonical", embedding_id="emb-canon")
        make_article(title="Dupe", embedding_id="emb-dupe", duplicate_of_id=canonical.id)

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [
                _chroma_hit("emb-dupe", 0.99),
                _chroma_hit("emb-canon", 0.90),
            ]
            hits = semantic_search(db_session, "AI news")

        assert len(hits) == 1
        assert hits[0].article.embedding_id == "emb-canon"

    def test_include_duplicates_flag_keeps_them(self, db_session, make_article):
        canonical = make_article(title="Canonical", embedding_id="emb-canon")
        make_article(title="Dupe", embedding_id="emb-dupe", duplicate_of_id=canonical.id)

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [
                _chroma_hit("emb-dupe", 0.99),
                _chroma_hit("emb-canon", 0.90),
            ]
            hits = semantic_search(db_session, "AI news", include_duplicates=True)

        assert len(hits) == 2

    def test_result_trimmed_to_n_results_after_filtering(self, db_session, make_article):
        for i in range(5):
            make_article(title=f"Article {i}", embedding_id=f"emb-{i}")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [_chroma_hit(f"emb-{i}", 0.9 - i * 0.1) for i in range(5)]
            hits = semantic_search(db_session, "AI news", n_results=2)

        assert len(hits) == 2

    def test_category_filter_passed_through_to_chroma_where_clause(self, db_session, make_article):
        make_article(title="Research article", embedding_id="emb-1", category="Research")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [_chroma_hit("emb-1", 0.9)]
            semantic_search(db_session, "AI news", category="Research")

        _, kwargs = mock_query.call_args
        assert kwargs.get("where") == {"category": "Research"}


class TestSearchEndpoint:
    def test_search_endpoint_missing_query_param(self, client):
        resp = client.get("/search")
        assert resp.status_code == 422

    def test_search_endpoint_empty_query_rejected(self, client):
        resp = client.get("/search", params={"q": ""})
        assert resp.status_code == 422

    def test_search_endpoint_returns_results(self, client, make_article):
        make_article(title="Matched article", embedding_id="emb-1")

        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = [_chroma_hit("emb-1", 0.85)]
            resp = client.get("/search", params={"q": "AI news"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "AI news"
        assert body["count"] == 1
        assert body["results"][0]["score"] == pytest.approx(0.85)
        assert body["results"][0]["article"]["title"] == "Matched article"

    def test_search_endpoint_no_hits_returns_empty_list(self, client):
        with patch("app.services.search_service.get_embedding_model", return_value=_fake_embedding_model()), \
             patch("app.services.search_service.get_vectorstore", return_value=MagicMock()), \
             patch("app.services.search_service.query_similar_with_scores") as mock_query:
            mock_query.return_value = []
            resp = client.get("/search", params={"q": "nothing matches this"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["results"] == []
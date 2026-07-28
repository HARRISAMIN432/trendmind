from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from app.schemas.article import ArticleListItem
from app.services import recommendation_service


def _article(url, category="Research", embedding_id="emb-1", title="Title"):
    return SimpleNamespace(url=url, category=category, embedding_id=embedding_id, title=title)


def _fake_from_orm_article(article):
    return ArticleListItem.model_construct(url=article.url, title=article.title, id=1)


class TestBuildCategoryProfile:
    def test_counts_categories_ignoring_missing(self):
        articles = [
            _article("u1", category="Research"),
            _article("u2", category="Research"),
            _article("u3", category=None),
        ]
        profile = recommendation_service._build_category_profile(articles)
        assert profile["Research"] == 2
        assert None not in profile

    def test_empty_input_returns_empty_counter(self):
        assert recommendation_service._build_category_profile([]) == {}


class TestAverageEmbedding:
    def test_averages_elementwise(self):
        result = recommendation_service._average_embedding([[1.0, 2.0], [3.0, 4.0]])
        assert result == [2.0, 3.0]

    def test_empty_input_returns_none(self):
        assert recommendation_service._average_embedding([]) is None

    def test_mismatched_length_vector_is_skipped_not_raised(self):
        # divisor stays len(vectors)=2 even though only one vector actually contributes
        result = recommendation_service._average_embedding([[1.0, 2.0], [1.0]])
        assert result == [0.5, 1.0]

    def test_single_vector_returns_itself(self):
        assert recommendation_service._average_embedding([[5.0, 5.0]]) == [5.0, 5.0]


class TestGetRecommendations:
    def test_no_read_articles_matched_returns_empty_fail_soft(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

        result = recommendation_service.get_recommendations(db, read_urls=["https://x.com/unread"])

        assert result.recommendations == []
        assert result.profile_categories == {}
        assert result.read_count_used == 0

    @patch(
        "app.services.recommendation_service.ArticleListItem.from_orm_article",
        side_effect=_fake_from_orm_article,
    )
    @patch("app.services.recommendation_service.query_similar_with_scores")
    @patch("app.services.recommendation_service.get_embeddings_by_ids")
    @patch("app.services.recommendation_service.get_vectorstore")
    @patch("app.services.recommendation_service.get_embedding_model")
    def test_excludes_already_read_urls_from_results(
        self, mock_model, mock_vectorstore, mock_get_embeddings, mock_query, mock_from_orm
    ):
        read_article = _article("https://x.com/read", embedding_id="emb-1")
        candidate = _article("https://x.com/new", category="Research")

        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [read_article]
        db.query.return_value.options.return_value.filter.return_value.filter.return_value.all.return_value = [
            candidate
        ]

        mock_get_embeddings.return_value = {"emb-1": [1.0, 0.0]}
        mock_query.return_value = [
            {"metadata": {"url": "https://x.com/read"}, "score": 0.99},
            {"metadata": {"url": "https://x.com/new"}, "score": 0.8},
        ]

        result = recommendation_service.get_recommendations(db, read_urls=["https://x.com/read"])

        urls = [r.article.url for r in result.recommendations]
        assert "https://x.com/read" not in urls
        assert "https://x.com/new" in urls
        assert result.read_count_used == 1

    @patch(
        "app.services.recommendation_service.ArticleListItem.from_orm_article",
        side_effect=_fake_from_orm_article,
    )
    @patch("app.services.recommendation_service.query_similar_with_scores")
    @patch("app.services.recommendation_service.get_embeddings_by_ids")
    @patch("app.services.recommendation_service.get_vectorstore")
    @patch("app.services.recommendation_service.get_embedding_model")
    def test_category_boost_ranks_matching_category_higher(
        self, mock_model, mock_vectorstore, mock_get_embeddings, mock_query, mock_from_orm
    ):
        read_article = _article("https://x.com/read", category="Research", embedding_id="emb-1")
        match = _article("https://x.com/match", category="Research")
        nomatch = _article("https://x.com/nomatch", category="Funding")

        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [read_article]
        db.query.return_value.options.return_value.filter.return_value.filter.return_value.all.return_value = [
            match,
            nomatch,
        ]

        mock_get_embeddings.return_value = {"emb-1": [1.0, 0.0]}
        # identical base similarity score - only the category boost should differentiate them
        mock_query.return_value = [
            {"metadata": {"url": "https://x.com/match"}, "score": 0.5},
            {"metadata": {"url": "https://x.com/nomatch"}, "score": 0.5},
        ]

        result = recommendation_service.get_recommendations(
            db, read_urls=["https://x.com/read"], category_boost=0.2
        )

        scores = {r.article.url: r.score for r in result.recommendations}
        matched_flags = {r.article.url: r.matched_category for r in result.recommendations}

        assert scores["https://x.com/match"] > scores["https://x.com/nomatch"]
        assert matched_flags["https://x.com/match"] is True
        assert matched_flags["https://x.com/nomatch"] is False
        assert result.recommendations[0].article.url == "https://x.com/match"

    def test_embedding_lookup_failure_fails_soft(self):
        read_article = _article("https://x.com/read")
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [read_article]

        with patch(
            "app.services.recommendation_service.get_embedding_model",
            side_effect=RuntimeError("boom"),
        ):
            result = recommendation_service.get_recommendations(db, read_urls=["https://x.com/read"])

        assert result.recommendations == []
        assert result.read_count_used == 1
        assert result.profile_categories == {"Research": 1}

    @patch("app.services.recommendation_service.query_similar_with_scores")
    @patch("app.services.recommendation_service.get_embeddings_by_ids")
    @patch("app.services.recommendation_service.get_vectorstore")
    @patch("app.services.recommendation_service.get_embedding_model")
    def test_similarity_query_failure_fails_soft(
        self, mock_model, mock_vectorstore, mock_get_embeddings, mock_query
    ):
        read_article = _article("https://x.com/read", embedding_id="emb-1")
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [read_article]

        mock_get_embeddings.return_value = {"emb-1": [1.0, 0.0]}
        mock_query.side_effect = RuntimeError("chroma unavailable")

        result = recommendation_service.get_recommendations(db, read_urls=["https://x.com/read"])

        assert result.recommendations == []
        assert result.read_count_used == 1

    @patch(
        "app.services.recommendation_service.ArticleListItem.from_orm_article",
        side_effect=_fake_from_orm_article,
    )
    @patch("app.services.recommendation_service.query_similar_with_scores")
    @patch("app.services.recommendation_service.get_embeddings_by_ids")
    @patch("app.services.recommendation_service.get_vectorstore")
    @patch("app.services.recommendation_service.get_embedding_model")
    def test_limit_truncates_results(
        self, mock_model, mock_vectorstore, mock_get_embeddings, mock_query, mock_from_orm
    ):
        read_article = _article("https://x.com/read", embedding_id="emb-1")
        candidates = [_article(f"https://x.com/c{i}") for i in range(5)]

        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [read_article]
        db.query.return_value.options.return_value.filter.return_value.filter.return_value.all.return_value = (
            candidates
        )

        mock_get_embeddings.return_value = {"emb-1": [1.0, 0.0]}
        mock_query.return_value = [
            {"metadata": {"url": c.url}, "score": 0.9 - i * 0.01} for i, c in enumerate(candidates)
        ]

        result = recommendation_service.get_recommendations(
            db, read_urls=["https://x.com/read"], limit=2
        )

        assert len(result.recommendations) == 2
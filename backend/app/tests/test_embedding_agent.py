"""
Unit tests for M06 — Embedding Agent (LangChain-based revision).

The LangChain `HuggingFaceEmbeddings` model and the Chroma vectorstore are
both mocked -- no model download and no on-disk Chroma DB needed to run
these, matching the mocking pattern used for LLM calls in M04/M05.
"""

from unittest.mock import MagicMock, patch

from app.agents.embedding_agent import (
    EmbeddedArticle,
    EmbeddingError,
    build_embedding_id,
    build_embedding_text,
    embed_all,
    embed_article,
    embedding_node,
)
from app.agents.summarization_agent import SummarizedArticle


def make_summarized(url="https://example.com/a1", title="OpenAI ships new model", summary="A concise summary."):
    return SummarizedArticle(
        title=title,
        url=url,
        source_name="TechCrunch AI",
        published_at=None,
        raw_content="<html>...</html>",
        clean_content="Some clean text " * 50,
        category="Product Launch",
        sub_category="Model Release",
        companies=["OpenAI"],
        importance="High",
        summary_short=summary,
        key_takeaway="Key takeaway.",
        why_it_matters="Why it matters.",
        technical_highlights="",
    )


class FakeEmbeddings:
    """Deterministic fake standing in for LangChain's HuggingFaceEmbeddings."""

    def embed_query(self, text):
        seed = sum(ord(c) for c in text) % 97
        return [float(seed), 1.0, 0.0]

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]


class TestBuildEmbeddingText:
    def test_combines_title_and_summary(self):
        article = make_summarized(title="Title X", summary="Summary Y")
        text = build_embedding_text(article)
        assert "Title X" in text
        assert "Summary Y" in text


class TestBuildEmbeddingId:
    def test_deterministic_for_same_url(self):
        assert build_embedding_id("https://a.com") == build_embedding_id("https://a.com")

    def test_different_for_different_urls(self):
        assert build_embedding_id("https://a.com") != build_embedding_id("https://b.com")

    def test_is_64_hex_chars(self):
        eid = build_embedding_id("https://a.com")
        assert len(eid) == 64
        int(eid, 16)  # raises if not valid hex


class TestEmbedArticle:
    def test_normal_embedding_uses_embed_query(self):
        article = make_summarized()
        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=FakeEmbeddings()
        ):
            result, error = embed_article(article)

        assert error is None
        assert isinstance(result, EmbeddedArticle)
        assert result.embedding_id == build_embedding_id(article.url)
        assert isinstance(result.embedding, list)
        assert result.title == article.title

    def test_empty_title_and_summary_rejected_without_model_call(self):
        article = make_summarized(title="", summary="")
        with patch("app.agents.embedding_agent.get_embedding_model") as mocked:
            result, error = embed_article(article)

        mocked.assert_not_called()
        assert result is None
        assert "nothing to embed" in error.reason

    def test_encode_failure_isolated(self):
        article = make_summarized()
        broken_model = MagicMock()
        broken_model.embed_query.side_effect = RuntimeError("model blew up")
        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=broken_model
        ):
            result, error = embed_article(article)

        assert result is None
        assert isinstance(error, EmbeddingError)
        assert "model blew up" in error.reason


class TestEmbedAll:
    def test_batch_isolates_empty_articles_before_batch_call(self):
        good = make_summarized(url="https://example.com/good")
        bad = make_summarized(url="https://example.com/bad", title="", summary="")

        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=FakeEmbeddings()
        ):
            embedded, errors = embed_all([good, bad], write_to_chroma=False)

        assert len(embedded) == 1
        assert embedded[0].url == "https://example.com/good"
        assert len(errors) == 1
        assert errors[0].url == "https://example.com/bad"

    def test_uses_embed_documents_once_for_whole_batch(self):
        articles = [make_summarized(url=f"https://example.com/{i}") for i in range(3)]
        fake = FakeEmbeddings()
        with patch.object(
            fake, "embed_documents", wraps=fake.embed_documents
        ) as spy, patch("app.agents.embedding_agent.get_embedding_model", return_value=fake):
            embedded, errors = embed_all(articles, write_to_chroma=False)

        assert len(embedded) == 3
        spy.assert_called_once()  # one batched call, not one per article

    def test_batch_encode_failure_errors_all_remaining_articles(self):
        good = make_summarized(url="https://example.com/a")
        also_good = make_summarized(url="https://example.com/b")
        broken_model = MagicMock()
        broken_model.embed_documents.side_effect = RuntimeError("batch call failed")

        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=broken_model
        ):
            embedded, errors = embed_all([good, also_good], write_to_chroma=False)

        assert embedded == []
        assert len(errors) == 2
        assert all("batch call failed" in e.reason for e in errors)

    def test_writes_to_chroma_when_enabled(self):
        good = make_summarized(url="https://example.com/good")
        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=FakeEmbeddings()
        ), patch(
            "app.agents.embedding_agent.get_vectorstore"
        ) as mock_get_vs, patch(
            "app.agents.embedding_agent.upsert_embeddings"
        ) as mock_upsert:
            mock_get_vs.return_value = "fake-vectorstore"
            embedded, errors = embed_all([good], write_to_chroma=True)

        assert len(embedded) == 1
        mock_upsert.assert_called_once()
        _, kwargs = mock_upsert.call_args
        assert kwargs["ids"] == [embedded[0].embedding_id]

    def test_empty_batch_skips_chroma_entirely(self):
        with patch("app.agents.embedding_agent.get_vectorstore") as mock_get_vs:
            embedded, errors = embed_all([], write_to_chroma=True)

        mock_get_vs.assert_not_called()
        assert embedded == []
        assert errors == []


class TestEmbeddingNode:
    def test_state_contract(self):
        state = {"articles": [make_summarized()]}
        with patch(
            "app.agents.embedding_agent.get_embedding_model", return_value=FakeEmbeddings()
        ), patch("app.agents.embedding_agent.get_vectorstore"), patch(
            "app.agents.embedding_agent.upsert_embeddings"
        ):
            new_state = embedding_node(state)

        assert "embedding_errors" in new_state
        assert len(new_state["articles"]) == 1
        assert isinstance(new_state["articles"][0], EmbeddedArticle)

    def test_missing_articles_key_defaults_to_empty(self):
        new_state = embedding_node({})
        assert new_state["articles"] == []
        assert new_state["embedding_errors"] == []

    def test_failed_articles_dropped_not_passed_through(self):
        state = {"articles": [make_summarized(title="", summary="")]}
        new_state = embedding_node(state)
        assert new_state["articles"] == []
        assert len(new_state["embedding_errors"]) == 1
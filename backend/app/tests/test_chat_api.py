"""
Tests for M11 - RAG Chat API.

Mocks app.services.rag_service.run_structured and semantic_search directly -
same "mock the call site, not the SDK" pattern as M04/M05/M10's suites.
No live Groq/Gemini call or live Chroma collection required.

Run with: pytest backend/tests/test_chat_api.py -v
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest

from app.agents.llm_client import LLMCallError
from app.agents.prompts.chat_prompt import ChatAnswer
from app.services.rag_service import answer_chat_question
from app.services.search_service import SearchHit


def _hit(article, score: float) -> SearchHit:
    return SearchHit(article=article, score=score)


class TestAnswerChatQuestion:
    def test_normal_answer_with_valid_citation(self, db_session, make_article):
        a = make_article(title="OpenAI ships new model", url="https://example.com/openai-model")

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.9)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (
                ChatAnswer(answer="OpenAI released a new model.", cited_urls=[a.url]),
                None,
            )
            resp = answer_chat_question(db_session, "What did OpenAI release?")

        assert resp.answer == "OpenAI released a new model."
        assert resp.context_article_count == 1
        assert len(resp.citations) == 1
        assert resp.citations[0].article.url == a.url
        assert resp.citations[0].relevance_score == pytest.approx(0.9)

    def test_llm_hallucinated_url_is_dropped(self, db_session, make_article):
        a = make_article(title="Real article", url="https://example.com/real")

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.8)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (
                ChatAnswer(answer="Some answer.", cited_urls=["https://example.com/made-up-url"]),
                None,
            )
            resp = answer_chat_question(db_session, "Question?")

        # The hallucinated URL doesn't match any retrieved hit, so it's dropped;
        # falls back to citing the real retrieval set rather than being empty.
        assert len(resp.citations) == 1
        assert resp.citations[0].article.url == a.url

    def test_llm_returns_no_citations_falls_back_to_retrieval_set(self, db_session, make_article):
        a1 = make_article(title="Article one", url="https://example.com/one")
        a2 = make_article(title="Article two", url="https://example.com/two")

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a1, 0.9), _hit(a2, 0.7)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (ChatAnswer(answer="General answer.", cited_urls=[]), None)
            resp = answer_chat_question(db_session, "Question?")

        assert len(resp.citations) == 2
        assert resp.context_article_count == 2

    def test_llm_failure_returns_soft_error_not_exception(self, db_session, make_article):
        a = make_article(title="Fallback article", url="https://example.com/fallback")

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.85)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (None, LLMCallError(stage="gemini", message="both providers down"))
            resp = answer_chat_question(db_session, "Question?")

        assert "couldn't generate an answer" in resp.answer.lower()
        assert "both providers down" in resp.answer
        # Still surfaces the raw retrieval hits as citations rather than an empty response.
        assert len(resp.citations) == 1
        assert resp.citations[0].article.url == a.url

    def test_no_retrieval_hits_and_llm_failure_yields_empty_citations(self, db_session):
        with patch("app.services.rag_service.semantic_search", return_value=[]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (None, LLMCallError(stage="no_provider", message="no keys set"))
            resp = answer_chat_question(db_session, "Question?")

        assert resp.citations == []
        assert resp.context_article_count == 0

    def test_history_and_n_context_articles_passed_through_to_search(self, db_session, make_article):
        a = make_article(title="Article", url="https://example.com/a")
        from app.schemas.chat import ChatTurn

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.5)]) as mock_search, \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (ChatAnswer(answer="ok", cited_urls=[]), None)
            answer_chat_question(
                db_session, "Follow-up question?",
                history=[ChatTurn(role="user", content="Earlier question")],
                n_context_articles=3,
                category="Research",
            )

        _, kwargs = mock_search.call_args
        assert kwargs["n_results"] == 3
        assert kwargs["category"] == "Research"

    def test_prompt_includes_history_when_provided(self, db_session, make_article):
        a = make_article(title="Article", url="https://example.com/a")
        from app.schemas.chat import ChatTurn

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.5)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (ChatAnswer(answer="ok", cited_urls=[]), None)
            answer_chat_question(
                db_session, "Follow-up question?",
                history=[ChatTurn(role="user", content="Earlier question text")],
            )

        prompt_arg = mock_run.call_args[0][0]
        assert "Earlier question text" in prompt_arg
        assert "Conversation so far" in prompt_arg


class TestChatEndpoint:
    def test_chat_endpoint_returns_answer(self, client, make_article):
        a = make_article(title="Endpoint article", url="https://example.com/endpoint")

        with patch("app.services.rag_service.semantic_search", return_value=[_hit(a, 0.9)]), \
             patch("app.services.rag_service.run_structured") as mock_run:
            mock_run.return_value = (
                ChatAnswer(answer="Answer text.", cited_urls=[a.url]),
                None,
            )
            resp = client.post("/chat", json={"question": "What happened?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Answer text."
        assert body["context_article_count"] == 1
        assert body["citations"][0]["article"]["url"] == a.url

    def test_chat_endpoint_empty_question_rejected(self, client):
        resp = client.post("/chat", json={"question": ""})
        assert resp.status_code == 422

    def test_chat_endpoint_invalid_history_role_rejected(self, client):
        resp = client.post("/chat", json={
            "question": "Hi",
            "history": [{"role": "system", "content": "not allowed"}],
        })
        assert resp.status_code == 422

    def test_chat_endpoint_n_context_articles_bounds(self, client):
        resp = client.post("/chat", json={"question": "Hi", "n_context_articles": 0})
        assert resp.status_code == 422

        resp2 = client.post("/chat", json={"question": "Hi", "n_context_articles": 16})
        assert resp2.status_code == 422
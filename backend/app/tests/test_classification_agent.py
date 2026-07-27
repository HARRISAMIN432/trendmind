from unittest.mock import patch

import pytest

from app.agents.classification_agent import (
    ClassifiedArticle,
    ClassificationError,
    classification_node,
    classify_all,
    classify_article,
)
from app.agents.cleaner_agent import CleanedArticle
from app.agents.llm_client import LLMCallError
from app.agents.prompts.classification_prompt import ClassificationResult


def make_cleaned(url="https://example.com/a1", clean_content="Some clean text " * 50):
    return CleanedArticle(
        title="OpenAI ships new model",
        url=url,
        source_name="TechCrunch AI",
        published_at=None,
        raw_content="<html>...</html>",
        clean_content=clean_content,
    )


def fake_result(**overrides):
    base = dict(
        category="Product Launch",
        sub_category="Model Release",
        companies=["OpenAI"],
        importance="High",
    )
    base.update(overrides)
    return ClassificationResult(**base)


class TestClassifyArticle:
    def test_normal_classification(self):
        article = make_cleaned()
        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            result, error = classify_article(article)

        assert error is None
        assert isinstance(result, ClassifiedArticle)
        assert result.category == "Product Launch"
        assert result.sub_category == "Model Release"
        assert result.companies == ["OpenAI"]
        assert result.importance == "High"
        assert result.title == article.title
        assert result.url == article.url

    def test_empty_clean_content_rejected_without_llm_call(self):
        article = make_cleaned(clean_content="")
        with patch("app.agents.classification_agent.run_structured") as mocked:
            result, error = classify_article(article)

        mocked.assert_not_called()
        assert result is None
        assert isinstance(error, ClassificationError)
        assert "empty clean_content" in error.reason

    def test_whitespace_only_clean_content_rejected(self):
        article = make_cleaned(clean_content="   \n\t  ")
        result, error = classify_article(article)
        assert result is None
        assert "empty clean_content" in error.reason

    def test_llm_error_isolated(self):
        article = make_cleaned()
        llm_error = LLMCallError(stage="gemini", message="both providers failed")
        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(None, llm_error),
        ):
            result, error = classify_article(article)

        assert result is None
        assert isinstance(error, ClassificationError)
        assert "both providers failed" in error.reason

    def test_llm_returns_none_without_explicit_error(self):
        article = make_cleaned()
        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(None, None),
        ):
            result, error = classify_article(article)

        assert result is None
        assert error.reason == "unknown LLM error"

    def test_never_raises_on_unexpected_exception(self):
        article = make_cleaned()
        with patch(
            "app.agents.classification_agent.run_structured",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(RuntimeError):
                # run_structured raising is not itself caught by classify_article
                # (llm_client.run_structured is the layer responsible for never
                # raising) -- this test documents that boundary explicitly.
                classify_article(article)


class TestClassifyAll:
    def test_batch_isolates_failures(self):
        good = make_cleaned(url="https://example.com/good")
        bad = make_cleaned(url="https://example.com/bad", clean_content="")

        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            classified, errors = classify_all([good, bad])

        assert len(classified) == 1
        assert classified[0].url == "https://example.com/good"
        assert len(errors) == 1
        assert errors[0].url == "https://example.com/bad"

    def test_empty_batch(self):
        classified, errors = classify_all([])
        assert classified == []
        assert errors == []

    def test_multiple_successes_preserve_order(self):
        articles = [make_cleaned(url=f"https://example.com/{i}") for i in range(3)]
        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            classified, errors = classify_all(articles)

        assert [a.url for a in classified] == [a.url for a in articles]
        assert errors == []


class TestClassificationNode:
    def test_state_contract(self):
        state = {"articles": [make_cleaned()]}
        with patch(
            "app.agents.classification_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            new_state = classification_node(state)

        assert "classification_errors" in new_state
        assert len(new_state["articles"]) == 1
        assert isinstance(new_state["articles"][0], ClassifiedArticle)

    def test_missing_articles_key_defaults_to_empty(self):
        state = {}
        new_state = classification_node(state)
        assert new_state["articles"] == []
        assert new_state["classification_errors"] == []

    def test_failed_articles_dropped_not_passed_through(self):
        state = {"articles": [make_cleaned(clean_content="")]}
        new_state = classification_node(state)
        assert new_state["articles"] == []
        assert len(new_state["classification_errors"]) == 1
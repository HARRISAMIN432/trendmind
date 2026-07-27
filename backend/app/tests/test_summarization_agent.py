from unittest.mock import patch

from app.agents.classification_agent import ClassifiedArticle
from app.agents.llm_client import LLMCallError
from app.agents.prompts.summarization_prompt import SummarizationResult
from app.agents.summarization_agent import (
    SummarizationError,
    SummarizedArticle,
    summarization_node,
    summarize_all,
    summarize_article,
)


def make_classified(url="https://example.com/a1", clean_content="Some clean text " * 50):
    return ClassifiedArticle(
        title="OpenAI ships new model",
        url=url,
        source_name="TechCrunch AI",
        published_at=None,
        raw_content="<html>...</html>",
        clean_content=clean_content,
        category="Product Launch",
        sub_category="Model Release",
        companies=["OpenAI"],
        importance="High",
    )


def fake_result(**overrides):
    base = dict(
        summary_short="OpenAI released a new model with improved reasoning.",
        key_takeaway="The new model outperforms its predecessor on benchmarks.",
        why_it_matters="This raises the bar for competitors in the LLM space.",
        technical_highlights="Scores 12% higher on MMLU than the prior version.",
    )
    base.update(overrides)
    return SummarizationResult(**base)


class TestSummarizeArticle:
    def test_normal_summarization(self):
        article = make_classified()
        with patch(
            "app.agents.summarization_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            result, error = summarize_article(article)

        assert error is None
        assert isinstance(result, SummarizedArticle)
        assert result.summary_short.startswith("OpenAI released")
        assert result.category == "Product Launch"  # carried over from M04
        assert result.companies == ["OpenAI"]

    def test_empty_clean_content_rejected_without_llm_call(self):
        article = make_classified(clean_content="")
        with patch("app.agents.summarization_agent.run_structured") as mocked:
            result, error = summarize_article(article)

        mocked.assert_not_called()
        assert result is None
        assert "empty clean_content" in error.reason

    def test_llm_error_isolated(self):
        article = make_classified()
        llm_error = LLMCallError(stage="gemini", message="rate limited on both")
        with patch(
            "app.agents.summarization_agent.run_structured",
            return_value=(None, llm_error),
        ):
            result, error = summarize_article(article)

        assert result is None
        assert isinstance(error, SummarizationError)
        assert "rate limited on both" in error.reason

    def test_technical_highlights_can_be_empty_string(self):
        article = make_classified()
        with patch(
            "app.agents.summarization_agent.run_structured",
            return_value=(fake_result(technical_highlights=""), None),
        ):
            result, error = summarize_article(article)

        assert error is None
        assert result.technical_highlights == ""


class TestSummarizeAll:
    def test_batch_isolates_failures(self):
        good = make_classified(url="https://example.com/good")
        bad = make_classified(url="https://example.com/bad", clean_content="")

        with patch(
            "app.agents.summarization_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            summarized, errors = summarize_all([good, bad])

        assert len(summarized) == 1
        assert summarized[0].url == "https://example.com/good"
        assert len(errors) == 1
        assert errors[0].url == "https://example.com/bad"

    def test_empty_batch(self):
        summarized, errors = summarize_all([])
        assert summarized == []
        assert errors == []


class TestSummarizationNode:
    def test_state_contract(self):
        state = {"articles": [make_classified()]}
        with patch(
            "app.agents.summarization_agent.run_structured",
            return_value=(fake_result(), None),
        ):
            new_state = summarization_node(state)

        assert "summarization_errors" in new_state
        assert len(new_state["articles"]) == 1
        assert isinstance(new_state["articles"][0], SummarizedArticle)

    def test_missing_articles_key_defaults_to_empty(self):
        state = {}
        new_state = summarization_node(state)
        assert new_state["articles"] == []
        assert new_state["summarization_errors"] == []

    def test_failed_articles_dropped_not_passed_through(self):
        state = {"articles": [make_classified(clean_content="")]}
        new_state = summarization_node(state)
        assert new_state["articles"] == []
        assert len(new_state["summarization_errors"]) == 1
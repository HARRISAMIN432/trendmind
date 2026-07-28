from __future__ import annotations
from unittest.mock import patch

from app.agents.entity_extraction_agent import extract_entities
from app.agents.llm_client import LLMCallError
from app.agents.prompts.entity_prompt import (
    EntityExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
)


def test_extract_entities_rejects_empty_content_without_llm_call():
    with patch("app.agents.entity_extraction_agent.run_structured") as mock_run:
        result, error = extract_entities(1, "Title", "")

    mock_run.assert_not_called()
    assert result is None
    assert error.article_id == 1
    assert "empty" in error.reason


def test_extract_entities_rejects_none_content():
    with patch("app.agents.entity_extraction_agent.run_structured") as mock_run:
        result, error = extract_entities(1, "Title", None)

    mock_run.assert_not_called()
    assert result is None
    assert error is not None


def test_extract_entities_rejects_whitespace_only_content():
    with patch("app.agents.entity_extraction_agent.run_structured") as mock_run:
        result, error = extract_entities(1, "Title", "   \n\t  ")

    mock_run.assert_not_called()
    assert result is None
    assert error is not None


def test_extract_entities_success():
    fake_result = EntityExtractionResult(
        entities=[
            ExtractedEntity(name="Acme AI", type="Company"),
            ExtractedEntity(name="AcmeGPT", type="Model"),
        ],
        relationships=[
            ExtractedRelationship(source="Acme AI", target="AcmeGPT", relation="released")
        ],
    )
    with patch(
        "app.agents.entity_extraction_agent.run_structured", return_value=(fake_result, None)
    ):
        result, error = extract_entities(1, "Acme launches AcmeGPT", "Acme AI released AcmeGPT today.")

    assert error is None
    assert result.entities[0].name == "Acme AI"
    assert result.relationships[0].relation == "released"


def test_extract_entities_llm_failure_returns_error_with_message():
    with patch(
        "app.agents.entity_extraction_agent.run_structured",
        return_value=(None, LLMCallError(stage="no_provider", message="both down")),
    ):
        result, error = extract_entities(1, "Title", "Some clean content here.")

    assert result is None
    assert error.article_id == 1
    assert error.reason == "both down"


def test_extract_entities_llm_failure_with_no_error_object_still_reports_something():
    with patch("app.agents.entity_extraction_agent.run_structured", return_value=(None, None)):
        result, error = extract_entities(1, "Title", "Some clean content here.")

    assert result is None
    assert error.reason == "unknown LLM failure"
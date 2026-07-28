from __future__ import annotations
from dataclasses import dataclass
from app.agents.llm_client import run_structured
from app.agents.prompts.entity_prompt import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    EntityExtractionResult,
    build_entity_extraction_prompt,
)


@dataclass
class EntityExtractionError:
    article_id: int
    reason: str


def extract_entities(
    article_id: int, title: str, clean_content: str | None
) -> tuple[EntityExtractionResult | None, EntityExtractionError | None]:
    if not clean_content or not clean_content.strip():
        return None, EntityExtractionError(article_id=article_id, reason="empty clean_content")

    prompt = f"{ENTITY_EXTRACTION_SYSTEM_PROMPT}\n\n{build_entity_extraction_prompt(title, clean_content)}"
    result, error = run_structured(prompt, EntityExtractionResult)
    if result is None:
        return None, EntityExtractionError(
            article_id=article_id, reason=error.message if error else "unknown LLM failure"
        )
    return result, None
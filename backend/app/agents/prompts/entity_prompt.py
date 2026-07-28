from __future__ import annotations
from pydantic import BaseModel, Field

ENTITY_TYPES = ["Company", "Model", "Researcher", "Dataset", "Product"]


class ExtractedEntity(BaseModel):
    name: str = Field(description="Canonical name of the entity as it appears in the article.")
    type: str = Field(description=f"One of: {', '.join(ENTITY_TYPES)}.")


class ExtractedRelationship(BaseModel):
    source: str = Field(description="Name of the source entity - must match a name in `entities`.")
    target: str = Field(description="Name of the target entity - must match a name in `entities`.")
    relation: str = Field(
        description=(
            "Short verb phrase describing the relationship, e.g. 'released', "
            "'trained by', 'partnered with', 'acquired'."
        )
    )


class EntityExtractionResult(BaseModel):
    """Schema passed to run_structured for M14's per-article extraction step."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


ENTITY_EXTRACTION_SYSTEM_PROMPT = (
    "You extract named entities and relationships between them from a news article for "
    "a knowledge graph. Only extract entities explicitly named in the text - never invent "
    "researchers, datasets, or products that aren't mentioned. Every `source` and `target` "
    "in `relationships` must exactly match a `name` already listed in `entities`. If the "
    "article doesn't clearly state a relationship between two entities, omit it rather "
    "than guessing."
)


def build_entity_extraction_prompt(title: str, clean_content: str) -> str:
    # Same 6000-char truncation budget as M04's classification prompt - extraction
    # needs full-article context more than a summary would give, but still needs to
    # stay cheap on Groq's free tier.
    truncated = clean_content[:6000] if clean_content else ""
    return f"Title: {title}\n\nArticle:\n{truncated}"
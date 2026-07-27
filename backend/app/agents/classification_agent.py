from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
from app.agents.llm_client import run_structured
from app.agents.prompts.classification_prompt import (
    ClassificationResult,
    build_classification_prompt,
)

try:
    from app.agents.cleaner_agent import CleanedArticle
except ImportError:  
    from dataclasses import dataclass as _dc

    @_dc
    class CleanedArticle:  # type: ignore[no-redef]
        title: str
        url: str
        source_name: str
        published_at: Any
        raw_content: str
        clean_content: str


@dataclass
class ClassifiedArticle:
    title: str
    url: str
    source_name: str
    published_at: Any
    raw_content: str
    clean_content: str
    category: str
    sub_category: str
    companies: list[str] = field(default_factory=list)
    importance: str = "Medium"

    @classmethod
    def from_cleaned(
        cls, article: CleanedArticle, result: ClassificationResult
    ) -> "ClassifiedArticle":
        return cls(
            **asdict(article),
            category=result.category,
            sub_category=result.sub_category,
            companies=result.companies,
            importance=result.importance,
        )


@dataclass
class ClassificationError:
    url: str
    reason: str


def classify_article(
    article: CleanedArticle,
) -> tuple[ClassifiedArticle | None, ClassificationError | None]:
    """Classifies a single CleanedArticle. Never raises."""
    if not article.clean_content or not article.clean_content.strip():
        return None, ClassificationError(
            url=article.url, reason="empty clean_content, nothing to classify"
        )

    prompt = build_classification_prompt(article.title, article.clean_content)
    result, llm_error = run_structured(prompt, ClassificationResult)

    if llm_error is not None or result is None:
        reason = llm_error.message if llm_error else "unknown LLM error"
        return None, ClassificationError(url=article.url, reason=reason)

    try:
        return ClassifiedArticle.from_cleaned(article, result), None
    except Exception as exc:  # noqa: BLE001 - defensive, e.g. malformed field types
        return None, ClassificationError(
            url=article.url, reason=f"post-processing failure: {exc}"
        )


def classify_all(
    articles: list[CleanedArticle],
) -> tuple[list[ClassifiedArticle], list[ClassificationError]]:
    """Runs classify_article across a batch, isolating per-article failures."""
    classified: list[ClassifiedArticle] = []
    errors: list[ClassificationError] = []

    for article in articles:
        result, error = classify_article(article)
        if result is not None:
            classified.append(result)
        if error is not None:
            errors.append(error)

    return classified, errors


def classification_node(state: dict) -> dict:
    articles: list[CleanedArticle] = state.get("articles", [])
    classified, errors = classify_all(articles)

    state["articles"] = classified
    state["classification_errors"] = errors
    return state
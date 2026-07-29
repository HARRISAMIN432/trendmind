from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
from app.agents.llm_client import run_structured
from app.agents.prompts.summarization_prompt import (
    SummarizationResult,
    build_summarization_prompt,
)
try:
    from app.agents.classification_agent import ClassifiedArticle
except ImportError:  # pragma: no cover - only hit if M04 file isn't present yet
    from dataclasses import dataclass as _dc, field as _field

    @_dc
    class ClassifiedArticle:  # type: ignore[no-redef]
        title: str
        url: str
        source_name: str
        published_at: Any
        raw_content: str
        clean_content: str
        category: str
        sub_category: str
        companies: list[str] = _field(default_factory=list)
        importance: str = "Medium"


@dataclass
class SummarizedArticle:
    title: str
    url: str
    source_name: str
    published_at: Any
    raw_content: str
    clean_content: str
    category: str
    sub_category: str
    companies: list[str]
    importance: str
    summary_short: str
    key_takeaway: str
    why_it_matters: str
    technical_highlights: str

    @classmethod
    def from_classified(
        cls, article: ClassifiedArticle, result: SummarizationResult
    ) -> "SummarizedArticle":
        return cls(
            **asdict(article),
            summary_short=result.summary_short,
            key_takeaway=result.key_takeaway,
            why_it_matters=result.why_it_matters,
            technical_highlights=result.technical_highlights,
        )


@dataclass
class SummarizationError:
    url: str
    reason: str


def summarize_article(
    article: ClassifiedArticle,
) -> tuple[SummarizedArticle | None, SummarizationError | None]:
    """Summarizes a single ClassifiedArticle. Never raises."""
    if not article.clean_content or not article.clean_content.strip():
        return None, SummarizationError(
            url=article.url, reason="empty clean_content, nothing to summarize"
        )

    prompt = build_summarization_prompt(
        article.title,
        article.clean_content,
        category=article.category,
        sub_category=article.sub_category,
    )
    result, llm_error = run_structured(prompt, SummarizationResult)

    if llm_error is not None or result is None:
        reason = llm_error.message if llm_error else "unknown LLM error"
        return None, SummarizationError(url=article.url, reason=reason)

    try:
        return SummarizedArticle.from_classified(article, result), None
    except Exception as exc:  # noqa: BLE001
        return None, SummarizationError(
            url=article.url, reason=f"post-processing failure: {exc}"
        )


def summarize_all(
    articles: list[ClassifiedArticle],
) -> tuple[list[SummarizedArticle], list[SummarizationError]]:
    """Runs summarize_article across a batch, isolating per-article failures."""
    summarized: list[SummarizedArticle] = []
    errors: list[SummarizationError] = []

    for article in articles:
        result, error = summarize_article(article)
        if result is not None:
            summarized.append(result)
        if error is not None:
            errors.append(error)

    return summarized, errors


def summarization_node(state: dict) -> dict:
    """
    LangGraph-node-shaped wrapper for the M08 StateGraph.

    Reads state["articles"] (list[ClassifiedArticle] from M04's
    classification_node), overwrites it with list[SummarizedArticle], and
    writes state["summarization_errors"].

    Same "fail closed" decision as M03/M04: articles that fail summarization
    are dropped rather than carried forward with null summary fields, since
    M06 (Embedding) needs summary_short/clean_content to build embedding text.
    """
    articles: list[ClassifiedArticle] = state.get("articles", [])
    summarized, errors = summarize_all(articles)

    state["articles"] = summarized
    state["summarization_errors"] = errors
    print("SUMMARIZE:", len(summarized), "survived |", len(errors), "errors", "| sample:", errors[0].reason if errors else None)
    return state
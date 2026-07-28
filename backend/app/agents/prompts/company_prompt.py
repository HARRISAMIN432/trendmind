from __future__ import annotations
from pydantic import BaseModel, Field


class CompanyProfileSummary(BaseModel):
    """Schema passed to run_structured for M13's LLM synthesis step."""

    overview: str = Field(
        description=(
            "2-4 sentence synthesis of who this company is and what it has been doing, "
            "based only on the provided articles."
        )
    )
    timeline_highlights: list[str] = Field(
        default_factory=list,
        description=(
            "Chronological list of short (one sentence) notable events pulled from the "
            "articles, oldest first. Empty list if nothing distinct enough to call out."
        ),
    )
    products: list[str] = Field(
        default_factory=list,
        description=(
            "Distinct product/model names mentioned in connection with this company. "
            "Empty list if the articles don't name any."
        ),
    )
    funding_mentions: list[str] = Field(
        default_factory=list,
        description=(
            "Short one-sentence descriptions of any funding, investment, or valuation "
            "mentions. Empty list if none are present."
        ),
    )


COMPANY_SYSTEM_PROMPT = (
    "You are synthesizing a company intelligence profile from a set of news articles "
    "that mention the company. Only use facts present in the provided articles - never "
    "invent products, funding amounts, dates, or events. If the articles don't mention "
    "products or funding, return an empty list for those fields rather than guessing."
)


def build_company_prompt(company_name: str, articles: list[dict]) -> str:
    """
    articles: list of {"title", "published_at" (iso str or None), "category", "summary_short"}
    already sorted chronologically by the caller (company_service).
    """
    lines = [f"Company: {company_name}", "", "Articles (chronological):"]
    for i, a in enumerate(articles, start=1):
        lines.append(
            f"[{i}] {a['published_at'] or 'unknown date'} | {a['category'] or 'Uncategorized'} | "
            f"{a['title']}\n    {a['summary_short'] or ''}"
        )
    return "\n".join(lines)
from __future__ import annotations
from pydantic import BaseModel, Field


class TrendSummary(BaseModel):
    title: str = Field(description="A short, punchy headline (max ~12 words) naming the shared trend/story.")
    description: str = Field(description="2-3 sentences explaining what's happening and why it's trending, "
                                          "synthesized across all the given articles.")


TREND_SYSTEM_PROMPT = (
    "You are analyzing a cluster of AI news articles that all appear to be about the "
    "same emerging trend or story. Write a headline and description that captures what "
    "connects them. Do not invent facts not present in the articles. If the articles "
    "don't actually share a clear common thread, describe the most prominent shared theme."
)


def build_trend_prompt(articles: list[dict]) -> str:
    articles_block = "\n\n".join(
        f"[{i+1}] Title: {a['title']}\nSummary: {a.get('summary_short') or ''}\nCategory: {a.get('category') or 'Unknown'}"
        for i, a in enumerate(articles)
    )
    return f"Articles in this cluster:\n\n{articles_block}"
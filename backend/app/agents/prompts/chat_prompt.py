from __future__ import annotations
from pydantic import BaseModel, Field


class ChatAnswer(BaseModel):
    answer: str = Field(description="The synthesized answer to the user's question, written in plain prose.")
    cited_urls: list[str] = Field(
        default_factory=list,
        description="URLs of the retrieved articles actually used to support the answer. "
                    "Only include URLs that were provided in the context, never invent one.",
    )


CHAT_SYSTEM_PROMPT = (
    "You are TrendMind's news assistant. Answer the user's question using ONLY the "
    "provided article excerpts as context. Never invent facts, numbers, or sources not "
    "present in the context. If the context doesn't contain enough information to answer, "
    "say so plainly rather than guessing. Cite the URLs of articles you actually relied on."
)


def build_chat_prompt(
    question: str,
    context_articles: list[dict],
    history: list[dict] | None = None,
) -> str:
    context_block = "\n\n".join(
        f"[{i+1}] Title: {a['title']}\nURL: {a['url']}\nSummary: {a.get('summary_short') or (a.get('clean_content') or '')[:800]}"
        for i, a in enumerate(context_articles)
    ) or "(no relevant articles found)"

    history_block = ""
    if history:
        history_block = "\n\nConversation so far:\n" + "\n".join(
            f"{turn['role'].capitalize()}: {turn['content']}" for turn in history
        )

    return (
        f"Context articles:\n{context_block}"
        f"{history_block}\n\n"
        f"User question: {question}"
    )
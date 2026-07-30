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

class RouteDecision(BaseModel):
    needs_retrieval: bool = Field(
        description="True if answering this question requires looking up articles "
                    "from the news corpus. False for greetings, meta questions about "
                    "the assistant itself, or general chit-chat that needs no factual grounding."
    )


ROUTE_SYSTEM_PROMPT = (
    "You are a routing component for a news-chat assistant. Decide whether the "
    "user's message requires retrieving articles from a news corpus to answer "
    "well, or whether it can be answered directly (greetings, small talk, "
    "questions about what the assistant can do)."
)


def build_route_prompt(question: str, history: list[dict] | None = None) -> str:
    history_block = ""
    if history:
        history_block = "\n\nConversation so far:\n" + "\n".join(
            f"{turn['role'].capitalize()}: {turn['content']}" for turn in history[-4:]
        )
    return f"{history_block}\n\nUser message: {question}"

class DocScore(BaseModel):
    url: str = Field(description="The article's URL, copied exactly from the input.")
    relevance_score: float = Field(
        description="A score from 0.0 to 1.0 for how well this specific article "
                    "answers the user's question. 1.0 = directly and fully answers it, "
                    "0.0 = completely unrelated."
    )


class RetrievalGrade(BaseModel):
    scores: list[DocScore] = Field(
        description="One score per retrieved article, in the same order they were given."
    )


GRADE_SYSTEM_PROMPT = (
    "You are a strict relevance grader for a news-chat assistant. Given a user's "
    "question and a list of retrieved articles, score each article from 0.0 to 1.0 "
    "on how well it answers the question. Be strict - a tangentially related article "
    "should score low. Return exactly one score per article, using its URL to identify it."
)


def build_grade_prompt(question: str, context_articles: list[dict]) -> str:
    articles_text = "\n\n".join(
        f"[{i+1}] url: {a['url']}\ntitle: {a['title']}\n"
        f"{a.get('summary_short') or (a.get('clean_content') or '')[:300]}"
        for i, a in enumerate(context_articles)
    )
    return f"Question: {question}\n\nRetrieved articles:\n{articles_text}"
from __future__ import annotations
from pydantic import BaseModel, Field

class ChatAnswer(BaseModel):
    answer: str = Field(description="The synthesized answer to the user's question, written in plain prose.")
    cited_urls: list[str] = Field(
        default_factory=list,
        description="URLs of the retrieved articles actually used to support the answer. "
                    "Only include URLs that were provided in the context, never invent one.",
    )


CHAT_SYSTEM_PROMPT = """You are DigestAI's news assistant. You answer questions using ONLY the article excerpts given to you as context.

STRICT RULES - follow all of them, in order of priority:

1. NEVER invent facts, numbers, dates, quotes, or sources that are not explicitly present in the context articles. If you are not certain a claim is supported by the context, do not make it.

2. If the context is empty, or does not contain enough information to answer the question, say so plainly in one or two sentences. Do NOT guess, speculate, or fall back on general knowledge to fill the gap. Example: "The articles I have don't cover that specifically."

3. ONLY include a URL in cited_urls if you actually drew on that specific article to construct your answer. Do not cite an article just because it was present in the context - being present is not the same as being used. If your answer only ends up relying on 2 of the 5 given articles, cited_urls should contain exactly those 2, not all 5.

4. If you cite zero articles because none were actually needed to answer (e.g. you could only partially answer, or the question turned out to be unanswerable from context), leave cited_urls empty. An empty list is a valid and expected output, not an error to avoid.

5. Do not pad the answer with a summary of unrelated articles "just in case they're useful." If an article in the context doesn't bear on the question, ignore it completely - don't mention it, don't describe it, don't cite it.

6. Write in plain, direct prose. No meta-commentary about being an AI or about the context you were given."""


def build_chat_prompt(
    question: str,
    context_articles: list[dict],
    history: list[dict] | None = None,
) -> str:
    context_block = "\n\n".join(
        f"[{i+1}] Title: {a['title']}\nURL: {a['url']}\nSummary: {a.get('summary_short') or (a.get('clean_content') or '')[:800]}"
        for i, a in enumerate(context_articles)
    ) or "(no articles provided - nothing to ground an answer in)"

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
        description="True only if answering this message requires looking up specific "
                    "articles from the news corpus. False for anything that is not a "
                    "genuine informational question about news/topics in the corpus."
    )


ROUTE_SYSTEM_PROMPT = """You are the routing component for DigestAI, a news-chat assistant. Your only job: decide if the user's message needs article retrieval to answer well.

Set needs_retrieval = FALSE for:
- Greetings and small talk: "hey", "hi", "hello", "what's up", "thanks", "ok", "cool"
- Messages with no real informational content, even if phrased as a question: "how are you", "who are you", "can you help me"
- Meta questions about the assistant itself: "what can you do", "how does this work"
- Messages too short or vague to identify any actual topic

Set needs_retrieval = TRUE only for:
- Genuine questions about news, companies, events, trends, or topics that could plausibly be covered by a news corpus: "what's the latest on OpenAI", "any news about chip export bans", "summarize this week in AI"

When in doubt because the message is short, ambiguous, or content-free, default to FALSE. A wasted retrieval on a real question is a minor inefficiency; a retrieval triggered by "hey" produces garbage citations that actively damage user trust - so the failure modes are NOT symmetric. Bias toward FALSE.

Examples:
- "hey" -> needs_retrieval: false
- "hi there" -> needs_retrieval: false
- "thanks!" -> needs_retrieval: false
- "what's new with Anthropic this week" -> needs_retrieval: true
- "is there any news about the EU AI Act" -> needs_retrieval: true
- "what can you help me with" -> needs_retrieval: false
- "ok" -> needs_retrieval: false"""


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
        description="One score per retrieved article, in the same order they were given. "
                    "Must contain exactly one entry per article - no more, no fewer."
    )


GRADE_SYSTEM_PROMPT = """You are a strict relevance grader for DigestAI, a news-chat assistant. You score how well each retrieved article answers the user's question.

SCORING SCALE - use the full range, do not cluster scores in the middle or high end:
- 0.9-1.0: article directly and substantially answers the question
- 0.6-0.8: article is on-topic and partially useful, but doesn't fully answer it
- 0.3-0.5: article is loosely related (same general domain) but doesn't actually address the question
- 0.0-0.2: article is unrelated to the question

CRITICAL EDGE CASE - read this carefully: if the user's message is a greeting, small talk, or has no real informational content (e.g. "hey", "thanks", "ok", "how are you"), there is no genuine question to grade articles against. In this case, score EVERY article 0.0, regardless of the article's topic or quality. Do not try to find a way to make an article "relevant" to a message that isn't actually asking anything - that is a grading error, not helpfulness.

Be strict by default. A tangentially related article (same industry, different specific topic) should score low, not medium. Only score high when the article would genuinely help someone who asked that specific question.

Return exactly one score per article in the order given, matched by URL."""


def build_grade_prompt(question: str, context_articles: list[dict]) -> str:
    articles_text = "\n\n".join(
        f"[{i+1}] url: {a['url']}\ntitle: {a['title']}\n"
        f"{a.get('summary_short') or (a.get('clean_content') or '')[:300]}"
        for i, a in enumerate(context_articles)
    )
    return f"Question: {question}\n\nRetrieved articles:\n{articles_text}"
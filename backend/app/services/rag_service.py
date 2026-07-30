from __future__ import annotations
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agents.llm_client import run_structured
from app.agents.prompts.chat_prompt import CHAT_SYSTEM_PROMPT, ChatAnswer, build_chat_prompt
from app.agents.prompts.chat_prompt import (
    ROUTE_SYSTEM_PROMPT,      # new - see prompt additions below
    RouteDecision,            # new - see schema additions below
    GRADE_SYSTEM_PROMPT,      # new - see prompt additions below
    RetrievalGrade,           # new - see schema additions below
    build_route_prompt,       # new
    build_grade_prompt,       # new
)

RELEVANCE_THRESHOLD = 0.7
from app.schemas.article import ArticleListItem
from app.schemas.chat import ChatCitation, ChatResponse, ChatTurn
from app.services.search_service import semantic_search


class ChatState(TypedDict, total=False):
    db: Session
    question: str
    history: list[dict] | None
    n_context_articles: int
    category: str | None

    needs_retrieval: bool
    hits: list                       # SearchHit objects from semantic_search
    docs_match: bool

    answer_text: str
    citations: list[ChatCitation]
    context_article_count: int


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

import logging

logger = logging.getLogger("digestai.rag")

_TRIVIAL_MESSAGES = {
    "hey", "hi", "hello", "yo", "sup", "hiya", "howdy",
    "hey there", "hi there", "good morning", "good evening", "good afternoon",
    "thanks", "thank you", "ok", "okay", "cool", "nice",
}


def route_node(state: ChatState) -> ChatState:
    """Decide whether this question needs corpus retrieval at all."""
    question_normalized = state["question"].strip().lower()

    # Deterministic short-circuit: don't trust an LLM judgment call on
    # content-free input. This is what let "hey" reach retrieval before.
    if question_normalized in _TRIVIAL_MESSAGES or len(question_normalized) <= 3:
        logger.info("route_node: short-circuit, question=%r -> needs_retrieval=False", state["question"])
        state["needs_retrieval"] = False
        return state

    prompt = build_route_prompt(
        question=state["question"],
        history=state.get("history"),
    )
    full_prompt = f"{ROUTE_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, RouteDecision)

    # Fail open toward retrieval - if the router itself fails, better to
    # attempt a grounded answer than to silently skip the corpus.
    needs_retrieval = result.needs_retrieval if result is not None else True
    logger.info("route_node: question=%r needs_retrieval=%s", state["question"], needs_retrieval)
    state["needs_retrieval"] = needs_retrieval
    return state


def retrieve_and_grade_node(state: ChatState) -> ChatState:
    """Retrieve candidate articles, then score each one's relevance to the question.

    Docs scoring below RELEVANCE_THRESHOLD are dropped from `hits` before
    generation. If nothing clears the bar, docs_match is False and the
    no-match fallback fires.
    """
    hits = semantic_search(
        db=state["db"],
        query=state["question"],
        n_results=state.get("n_context_articles", 5),
        category=state.get("category"),
    )

    if not hits:
        state["hits"] = []
        state["docs_match"] = False
        return state

    # Raw-similarity floor: if the embedding search itself came back with
    # near-zero or negative cosine similarity, the corpus genuinely has
    # nothing close to this query - don't even bother asking the grading
    # LLM, which can be unreliable on a weak/ambiguous candidate set.
    hits = [h for h in hits if h.score >= 0.2]
    if not hits:
        logger.info("retrieve_and_grade_node: all hits below raw similarity floor, question=%r", state["question"])
        state["hits"] = []
        state["docs_match"] = False
        return state

    context_articles = [
        {
            "title": h.article.title,
            "url": h.article.url,
            "summary_short": h.article.summary_short,
            "clean_content": h.article.clean_content,
        }
        for h in hits
    ]
    prompt = build_grade_prompt(question=state["question"], context_articles=context_articles)
    full_prompt = f"{GRADE_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, RetrievalGrade)

    if result is None:
        # Fail CLOSED here - if grading is unavailable, we cannot verify
        # relevance, so don't hand ungraded docs to generation. Better to
        # give a no-match answer than risk citing irrelevant articles.
        logger.warning("retrieve_and_grade_node: grading call failed, failing closed. question=%r", state["question"])
        state["hits"] = []
        state["docs_match"] = False
        return state

    score_by_url = {s.url: s.relevance_score for s in result.scores}
    logger.info("retrieve_and_grade_node: scores=%s", score_by_url)
    filtered_hits = [h for h in hits if score_by_url.get(h.article.url, 0.0) >= RELEVANCE_THRESHOLD]

    state["hits"] = filtered_hits
    state["docs_match"] = len(filtered_hits) > 0
    return state


def generate_direct_node(state: ChatState) -> ChatState:
    """No retrieval needed - answer conversationally, no corpus grounding."""
    prompt = build_chat_prompt(
        question=state["question"],
        context_articles=[],
        history=state.get("history"),
    )
    full_prompt = f"{CHAT_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, ChatAnswer)

    state["answer_text"] = (
        result.answer if result is not None
        else "Hey! Ask me about recent AI news and I'll dig into the corpus for you."
    )
    state["citations"] = []
    state["context_article_count"] = 0
    return state


def generate_no_match_node(state: ChatState) -> ChatState:
    """Retrieved something, but it doesn't actually answer the question."""
    state["answer_text"] = (
        "I couldn't find any articles in the corpus that answer that directly. "
        "Try rephrasing, or ask about a different recent AI topic."
    )
    state["citations"] = []
    state["context_article_count"] = len(state.get("hits", []))
    return state


def generate_grounded_node(state: ChatState) -> ChatState:
    """Retrieved docs are relevant - generate the grounded, cited answer."""
    hits = state["hits"]
    context_articles = [
        {
            "title": h.article.title,
            "url": h.article.url,
            "summary_short": h.article.summary_short,
            "clean_content": h.article.clean_content,
        }
        for h in hits
    ]
    prompt = build_chat_prompt(
        question=state["question"],
        context_articles=context_articles,
        history=state.get("history"),
    )
    full_prompt = f"{CHAT_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, ChatAnswer)

    if result is None:
        state["answer_text"] = (
            "I couldn't generate an answer right now (both LLM providers failed"
            f"{': ' + error.message if error else ''}). Here are the most relevant "
            "articles I found instead."
        )
        cited_urls: list[str] = []
    else:
        state["answer_text"] = result.answer
        cited_urls = result.cited_urls

    score_by_url = {h.article.url: h.score for h in hits}
    hits_by_url = {h.article.url: h for h in hits}

    citations: list[ChatCitation] = []
    for url in cited_urls:
        hit = hits_by_url.get(url)
        if hit is None:
            continue
        citations.append(ChatCitation(
            article=ArticleListItem.from_orm_article(hit.article),
            relevance_score=score_by_url[url],
        ))

    # No fallback here on purpose - if the LLM cited nothing, show nothing.
    # Falling back to "all filtered hits" would surface docs the model never
    # actually used, which is misleading in the sources panel.
    state["citations"] = citations
    state["context_article_count"] = len(hits)
    return state


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def route_decision(state: ChatState) -> Literal["retrieve", "direct"]:
    return "retrieve" if state["needs_retrieval"] else "direct"


def grade_decision(state: ChatState) -> Literal["generate", "no_match"]:
    return "generate" if state["docs_match"] else "no_match"


# ---------------------------------------------------------------------------
# Graph assembly (built once, module-level)
# ---------------------------------------------------------------------------

def _build_graph():
    graph = StateGraph(ChatState)

    graph.add_node("route", route_node)
    graph.add_node("retrieve_and_grade", retrieve_and_grade_node)
    graph.add_node("generate_direct", generate_direct_node)
    graph.add_node("generate_no_match", generate_no_match_node)
    graph.add_node("generate_grounded", generate_grounded_node)

    graph.set_entry_point("route")

    graph.add_conditional_edges(
        "route",
        route_decision,
        {"retrieve": "retrieve_and_grade", "direct": "generate_direct"},
    )
    graph.add_conditional_edges(
        "retrieve_and_grade",
        grade_decision,
        {"generate": "generate_grounded", "no_match": "generate_no_match"},
    )

    graph.add_edge("generate_direct", END)
    graph.add_edge("generate_no_match", END)
    graph.add_edge("generate_grounded", END)

    return graph.compile()


_chat_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entrypoint - same signature as before, drop-in replacement
# ---------------------------------------------------------------------------

def answer_chat_question(
    db: Session,
    question: str,
    history: list[ChatTurn] | None = None,
    n_context_articles: int = 5,
    category: str | None = None,
) -> ChatResponse:
    initial_state: ChatState = {
        "db": db,
        "question": question,
        "history": [t.model_dump() for t in history] if history else None,
        "n_context_articles": n_context_articles,
        "category": category,
    }

    final_state = _chat_graph.invoke(initial_state)

    return ChatResponse(
        answer=final_state["answer_text"],
        citations=final_state["citations"],
        context_article_count=final_state["context_article_count"],
    )
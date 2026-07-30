from __future__ import annotations
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agents.llm_client import run_structured
from app.agents.prompts.chat_prompt import CHAT_SYSTEM_PROMPT, ChatAnswer, build_chat_prompt
from app.agents.prompts.chat_prompt import (
    ROUTE_SYSTEM_PROMPT,      
    RouteDecision,           
    GRADE_SYSTEM_PROMPT,      
    RetrievalGrade,          
    build_route_prompt,       
    build_grade_prompt,       
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
    hits: list                       
    docs_match: bool

    answer_text: str
    citations: list[ChatCitation]
    context_article_count: int

def route_node(state: ChatState) -> ChatState:
    """Decide whether this question needs corpus retrieval at all."""
    prompt = build_route_prompt(
        question=state["question"],
        history=state.get("history"),
    )
    full_prompt = f"{ROUTE_SYSTEM_PROMPT}\n\n{prompt}"
    result, error = run_structured(full_prompt, RouteDecision)

    needs_retrieval = result.needs_retrieval if result is not None else True
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
        # Fail open - grading unavailable, keep everything and let generation proceed.
        state["hits"] = hits
        state["docs_match"] = True
        return state

    score_by_url = {s.url: s.relevance_score for s in result.scores}
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

    if not citations:
        citations = [
            ChatCitation(article=ArticleListItem.from_orm_article(h.article), relevance_score=h.score)
            for h in hits
        ]

    state["citations"] = citations
    state["context_article_count"] = len(hits)
    return state

def route_decision(state: ChatState) -> Literal["retrieve", "direct"]:
    return "retrieve" if state["needs_retrieval"] else "direct"


def grade_decision(state: ChatState) -> Literal["generate", "no_match"]:
    return "generate" if state["docs_match"] else "no_match"

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
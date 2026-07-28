from __future__ import annotations
from sqlalchemy.orm import Session
from app.agents.llm_client import run_structured
from app.agents.prompts.chat_prompt import CHAT_SYSTEM_PROMPT, ChatAnswer, build_chat_prompt
from app.schemas.article import ArticleListItem
from app.schemas.chat import ChatCitation, ChatResponse, ChatTurn
from app.services.search_service import semantic_search


def answer_chat_question(
    db: Session,
    question: str,
    history: list[ChatTurn] | None = None,
    n_context_articles: int = 5,
    category: str | None = None,
) -> ChatResponse:
    hits = semantic_search(
        db=db, query=question, n_results=n_context_articles, category=category,
    )

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
        question=question,
        context_articles=context_articles,
        history=[t.model_dump() for t in history] if history else None,
    )
    full_prompt = f"{CHAT_SYSTEM_PROMPT}\n\n{prompt}"

    result, error = run_structured(full_prompt, ChatAnswer)

    if result is None:
        answer_text = (
            "I couldn't generate an answer right now (both LLM providers failed"
            f"{': ' + error.message if error else ''}). Here are the most relevant "
            "articles I found instead."
        )
        cited_urls: list[str] = []
    else:
        answer_text = result.answer
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

    return ChatResponse(
        answer=answer_text,
        citations=citations,
        context_article_count=len(hits),
    )
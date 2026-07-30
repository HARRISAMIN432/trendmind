from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import answer_chat_question
from app.middleware.limiter import limiter
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
# @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def chat(request: Request, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return answer_chat_question(
        db=db,
        question=payload.question,
        history=payload.history,
        n_context_articles=payload.n_context_articles,
        category=payload.category,
    )
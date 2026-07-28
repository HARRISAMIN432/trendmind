from __future__ import annotations
from pydantic import BaseModel, Field
from app.schemas.article import ArticleListItem


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ChatTurn] = Field(default_factory=list, description="Prior turns, oldest first. Not persisted server-side.")
    n_context_articles: int = Field(5, ge=1, le=15)
    category: str | None = None


class ChatCitation(BaseModel):
    article: ArticleListItem
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]
    context_article_count: int
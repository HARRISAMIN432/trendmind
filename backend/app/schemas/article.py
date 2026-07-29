from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    homepage_url: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    url: str
    published_at: datetime | None = None
    source_name: str | None = None
    category: str | None = None
    sub_category: str | None = None
    importance: str | None = None
    summary_short: str | None = None
    key_takeaway: str | None = None
    companies: list[str] = []
    is_duplicate: bool = False
    duplicate_of_id: int | None = None

    @classmethod
    def from_orm_article(cls, article) -> "ArticleListItem":
        return cls(
            id=article.id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            source_name=article.source.name if article.source else None,
            category=article.category,
            sub_category=article.sub_category,
            importance=article.importance,
            summary_short=article.summary_short,
            key_takeaway=article.key_takeaway,
            companies=[c.name for c in article.companies],
            is_duplicate=article.duplicate_of_id is not None,
            duplicate_of_id=article.duplicate_of_id,
        )


class ArticleDetail(ArticleListItem):
    clean_content: str | None = None
    why_it_matters: str | None = None
    technical_highlights: str | None = None
    embedding_id: str | None = None
    source: SourceRead | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_article(cls, article) -> "ArticleDetail":
        base = ArticleListItem.from_orm_article(article)
        return cls(
            **base.model_dump(),
            clean_content=article.clean_content,
            why_it_matters=article.why_it_matters,
            technical_highlights=article.technical_highlights,
            embedding_id=article.embedding_id,
            source=SourceRead.model_validate(article.source) if article.source else None,
            created_at=article.created_at,
            updated_at=article.updated_at,
        )


class ArticleCreate(BaseModel):
    title: str
    url: str
    published_at: datetime | None = None
    raw_content: str | None = None
    clean_content: str | None = None
    source_id: int | None = None
    category: str | None = None
    sub_category: str | None = None
    importance: str | None = None
    summary_short: str | None = None
    key_takeaway: str | None = None
    why_it_matters: str | None = None
    technical_highlights: str | None = None
    # BUG FIX: these two were missing entirely. Pydantic's default extra="ignore"
    # meant internal.py's ArticleCreate(embedding_id=..., duplicate_of_id=...)
    # calls never raised - the kwargs were just silently dropped at construction,
    # which is why every stored article had these NULL regardless of what the
    # pipeline computed for them.
    embedding_id: str | None = None
    duplicate_of_id: int | None = None
    company_names: list[str] = []


class ArticleUpdate(BaseModel):
    """Partial update — only curatable/editorial fields. Pipeline-owned fields
    (url, embedding_id, duplicate_of_id, raw_content) are not editable here."""
    category: str | None = None
    sub_category: str | None = None
    importance: str | None = None
    summary_short: str | None = None
    key_takeaway: str | None = None
    why_it_matters: str | None = None
    technical_highlights: str | None = None
    company_names: list[str] | None = None


class PaginatedArticles(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ArticleListItem]
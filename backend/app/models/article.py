from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.source import Source
    from app.models.trend import Trend

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    source: Mapped["Source"] = relationship(back_populates="articles")
    clean_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sub_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)  
    companies: Mapped[list["Company"]] = relationship(
        secondary="article_companies",
        back_populates="articles",
    )
    summary_short: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_takeaway: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_highlights: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_of: Mapped["Article"] = relationship(remote_side=[id])
    trends: Mapped[list["Trend"]] = relationship(
        secondary="trend_articles",
        back_populates="articles",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    def __repr__(self) -> str:
        return f"<Article id={self.id} title={self.title[:40]!r}>"
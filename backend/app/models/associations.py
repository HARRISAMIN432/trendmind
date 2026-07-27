from __future__ import annotations
from sqlalchemy import Table, Column, ForeignKey
from app.db.session import Base

article_companies = Table(
    "article_companies",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
)

trend_articles = Table(
    "trend_articles",
    Base.metadata,
    Column("trend_id", ForeignKey("trends.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
)
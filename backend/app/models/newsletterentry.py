from datetime import date, datetime
from sqlalchemy import Date, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class NewsletterEntry(Base):
    __tablename__ = "newsletter_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<NewsletterEntry id={self.id} date={self.digest_date}>"
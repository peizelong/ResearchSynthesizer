from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from synthesizer.database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(50))  # "jiuyan_web" | "xueqiu"
    source_article_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    crawled_at: Mapped[datetime]
    trust_level: Mapped[str] = mapped_column(String(1), default="C")
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    narratives: Mapped[list["ArticleNarrative"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


Index("ix_articles_source", Article.source)
Index("ix_articles_source_article_id", Article.source_article_id)

from synthesizer.models.narrative import ArticleNarrative  # noqa: E402

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import Article, ResearchBatch


class ArticleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Article:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "crawled_at" not in kwargs:
            kwargs["crawled_at"] = datetime.utcnow()
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.utcnow()
        article = Article(**kwargs)
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article

    def get(self, article_id: str) -> Article | None:
        return self.db.query(Article).filter(Article.id == article_id).first()

    def list(self, source: str | None = None, limit: int = 50, offset: int = 0) -> list[Article]:
        q = self.db.query(Article)
        if source:
            q = q.filter(Article.source == source)
        return q.order_by(Article.created_at.desc()).offset(offset).limit(limit).all()

    def count(self, source: str | None = None) -> int:
        q = self.db.query(Article)
        if source:
            q = q.filter(Article.source == source)
        return q.count()

    def get_pending_extraction(self, limit: int = 50) -> list[Article]:
        return (
            self.db.query(Article)
            .filter(Article.extraction_status == "pending")
            .order_by(Article.created_at.asc())
            .limit(limit)
            .all()
        )

    def update_extraction_status(self, article_id: str, status: str) -> None:
        self.db.query(Article).filter(Article.id == article_id).update({"extraction_status": status})
        self.db.commit()

    def upsert_by_source(self, source: str, source_article_id: str, **kwargs) -> Article:
        existing = (
            self.db.query(Article)
            .filter(Article.source == source, Article.source_article_id == source_article_id)
            .first()
        )
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        return self.create(source=source, source_article_id=source_article_id, **kwargs)

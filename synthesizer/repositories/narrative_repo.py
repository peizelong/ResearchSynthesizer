from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import ArticleNarrative


class NarrativeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> ArticleNarrative:
        kwargs.setdefault("id", str(uuid4()))
        kwargs.setdefault("extracted_at", datetime.utcnow())
        kwargs.setdefault("created_at", datetime.utcnow())
        narrative = ArticleNarrative(**kwargs)
        self.db.add(narrative)
        self.db.commit()
        self.db.refresh(narrative)
        return narrative

    def list_by_article(self, article_id: str) -> list[ArticleNarrative]:
        return (
            self.db.query(ArticleNarrative)
            .filter(ArticleNarrative.article_id == article_id)
            .all()
        )

    def delete_by_article(self, article_id: str) -> int:
        rows = (
            self.db.query(ArticleNarrative)
            .filter(ArticleNarrative.article_id == article_id)
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return rows

    def list_by_article_ids(self, article_ids: list[str]) -> list[ArticleNarrative]:
        if not article_ids:
            return []
        return (
            self.db.query(ArticleNarrative)
            .filter(ArticleNarrative.article_id.in_(article_ids))
            .all()
        )

    def list_by_batch(self, batch) -> list[ArticleNarrative]:
        return self.list_by_article_ids(batch.article_ids or [])

    def get(self, narrative_id: str) -> ArticleNarrative | None:
        return (
            self.db.query(ArticleNarrative)
            .filter(ArticleNarrative.id == narrative_id)
            .first()
        )

    def count(self) -> int:
        return self.db.query(ArticleNarrative).count()

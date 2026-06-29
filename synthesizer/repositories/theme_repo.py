from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import MergedTheme


class ThemeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> MergedTheme:
        kwargs.setdefault("id", str(uuid4()))
        kwargs.setdefault("created_at", datetime.utcnow())
        kwargs.setdefault("updated_at", datetime.utcnow())
        theme = MergedTheme(**kwargs)
        self.db.add(theme)
        self.db.commit()
        self.db.refresh(theme)
        return theme

    def get(self, theme_id: str) -> MergedTheme | None:
        return self.db.query(MergedTheme).filter(MergedTheme.id == theme_id).first()

    def list_by_batch(self, batch_id: str) -> list[MergedTheme]:
        return (
            self.db.query(MergedTheme)
            .filter(MergedTheme.batch_id == batch_id)
            .order_by(MergedTheme.member_count.desc())
            .all()
        )

    def list(self, batch_id: str | None = None, limit: int = 50, offset: int = 0) -> list[MergedTheme]:
        q = self.db.query(MergedTheme)
        if batch_id:
            q = q.filter(MergedTheme.batch_id == batch_id)
        return q.order_by(MergedTheme.member_count.desc()).offset(offset).limit(limit).all()

    def update(self, theme_id: str, **fields) -> MergedTheme | None:
        theme = self.get(theme_id)
        if not theme:
            return None
        for k, v in fields.items():
            setattr(theme, k, v)
        theme.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(theme)
        return theme

    def delete_by_batch(self, batch_id: str) -> int:
        rows = self.db.query(MergedTheme).filter(MergedTheme.batch_id == batch_id).delete(
            synchronize_session="fetch"
        )
        self.db.commit()
        return rows

    def count(self) -> int:
        return self.db.query(MergedTheme).count()

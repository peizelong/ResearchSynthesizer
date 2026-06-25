from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import ResearchBatch


class BatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> ResearchBatch:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.utcnow()
        batch = ResearchBatch(**kwargs)
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get(self, batch_id: str) -> ResearchBatch | None:
        return self.db.query(ResearchBatch).filter(ResearchBatch.id == batch_id).first()

    def list(self, limit: int = 50, offset: int = 0) -> list[ResearchBatch]:
        return (
            self.db.query(ResearchBatch)
            .order_by(ResearchBatch.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_status(self, batch_id: str, status: str, stage: str | None = None, error: str | None = None) -> None:
        updates = {"status": status}
        if stage:
            updates["current_stage"] = stage
        if error:
            updates["error_message"] = error
        if status == "running" and not self.get(batch_id).started_at:
            updates["started_at"] = datetime.utcnow()
        if status in ("completed", "failed"):
            updates["finished_at"] = datetime.utcnow()
        self.db.query(ResearchBatch).filter(ResearchBatch.id == batch_id).update(updates)
        self.db.commit()

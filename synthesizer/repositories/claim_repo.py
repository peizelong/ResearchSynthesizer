from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import Claim


class ClaimRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Claim:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "extracted_at" not in kwargs:
            kwargs["extracted_at"] = datetime.utcnow()
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.utcnow()
        claim = Claim(**kwargs)
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def bulk_create(self, claims: list[dict]) -> list[Claim]:
        objects = []
        for c in claims:
            c.setdefault("id", str(uuid4()))
            c.setdefault("extracted_at", datetime.utcnow())
            c.setdefault("created_at", datetime.utcnow())
            objects.append(Claim(**c))
        self.db.bulk_save_objects(objects)
        self.db.commit()
        return objects

    def list_by_article(self, article_id: str) -> list[Claim]:
        return self.db.query(Claim).filter(Claim.article_id == article_id).all()

    def list_by_batch(self, batch) -> list[Claim]:
        """通过 batch.article_ids 查 claims"""
        if not batch.article_ids:
            return []
        return self.list_by_article_ids(batch.article_ids)

    def list_by_article_ids(self, article_ids: list[str]) -> list[Claim]:
        if not article_ids:
            return []
        return self.db.query(Claim).filter(Claim.article_id.in_(article_ids)).all()

    def list_by_cluster(self, cluster_id: str) -> list[Claim]:
        return self.db.query(Claim).filter(Claim.topic_cluster_id == cluster_id).all()

    def assign_cluster(self, claim_ids: list[str], cluster_id: str) -> None:
        self.db.query(Claim).filter(Claim.id.in_(claim_ids)).update(
            {"topic_cluster_id": cluster_id}, synchronize_session="fetch"
        )
        self.db.commit()

    def count(self) -> int:
        return self.db.query(Claim).count()

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from synthesizer.models import TopicCluster, Claim


class ClusterRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> TopicCluster:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid4())
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.utcnow()
        cluster = TopicCluster(**kwargs)
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        return cluster

    def get(self, cluster_id: str) -> TopicCluster | None:
        return self.db.query(TopicCluster).filter(TopicCluster.id == cluster_id).first()

    def list(self, batch_id: str | None = None, limit: int = 50, offset: int = 0) -> list[TopicCluster]:
        q = self.db.query(TopicCluster)
        if batch_id:
            q = q.filter(TopicCluster.batch_id == batch_id)
        return q.order_by(TopicCluster.member_count.desc()).offset(offset).limit(limit).all()

    def list_by_batch(self, batch_id: str) -> list[TopicCluster]:
        return (
            self.db.query(TopicCluster)
            .filter(TopicCluster.batch_id == batch_id)
            .order_by(TopicCluster.member_count.desc())
            .all()
        )

    def get_claims(self, cluster_id: str) -> list[Claim]:
        return self.db.query(Claim).filter(Claim.topic_cluster_id == cluster_id).all()

    def count(self) -> int:
        return self.db.query(TopicCluster).count()

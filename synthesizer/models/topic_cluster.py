from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from synthesizer.database import Base


class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("research_batches.id"))
    # 聚类结果
    cluster_label: Mapped[str] = mapped_column(String(200))
    cluster_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_claim_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # 统计（后置填充）
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    angle_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 聚类元数据
    cluster_method: Mapped[str] = mapped_column(String(30), default="rule")  # rule|embedding|llm
    coherence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    claims: Mapped[list["Claim"]] = relationship(back_populates="topic_cluster")


Index("ix_clusters_batch_id", TopicCluster.batch_id)
Index("ix_clusters_label", TopicCluster.cluster_label)

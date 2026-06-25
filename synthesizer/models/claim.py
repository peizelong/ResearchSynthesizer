from datetime import datetime
from sqlalchemy import String, Text, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from synthesizer.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"))
    # 抽取内容
    claim_type: Mapped[str] = mapped_column(String(30))  # direction|fact|prediction|causality
    subject: Mapped[str] = mapped_column(String(200))
    predicate: Mapped[str] = mapped_column(String(200))
    object_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    direction_tag: Mapped[str | None] = mapped_column(String(200), nullable=True)
    direction_angle: Mapped[str | None] = mapped_column(String(30), nullable=True)  # policy|industry|company|tech|macro
    # 证据
    evidence_text: Mapped[str] = mapped_column(Text)
    # 元数据
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    extractor_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    # 聚类关联（后置填充）
    topic_cluster_id: Mapped[str | None] = mapped_column(ForeignKey("topic_clusters.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="claims")
    topic_cluster: Mapped["TopicCluster | None"] = relationship(back_populates="claims")


Index("ix_claims_article_id", Claim.article_id)
Index("ix_claims_direction_tag", Claim.direction_tag)
Index("ix_claims_cluster_id", Claim.topic_cluster_id)

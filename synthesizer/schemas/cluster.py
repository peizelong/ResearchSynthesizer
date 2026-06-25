from datetime import datetime
from pydantic import BaseModel, Field


class ClusterResponse(BaseModel):
    id: str
    batch_id: str
    cluster_label: str
    cluster_summary: str | None = None
    representative_claim_id: str | None = None
    member_count: int
    article_count: int
    angle_distribution: dict | None = None
    source_distribution: dict | None = None
    cluster_method: str
    coherence_score: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClusterDetailResponse(ClusterResponse):
    claims: list[dict] = Field(default_factory=list)

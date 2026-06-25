from datetime import datetime
from pydantic import BaseModel


class ClaimResponse(BaseModel):
    id: str
    article_id: str
    claim_type: str
    subject: str
    predicate: str
    object_value: str | None = None
    direction_tag: str | None = None
    direction_angle: str | None = None
    evidence_text: str
    confidence: float
    extractor_model: str | None = None
    extracted_at: datetime
    topic_cluster_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime
from pydantic import BaseModel, Field


class BatchCreateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    article_ids: list[str] | None = None
    source_filter: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    config: dict | None = None


class BatchResponse(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    article_ids: list[str] = Field(default_factory=list)
    source_filter: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: str
    current_stage: str | None = None
    error_message: str | None = None
    config: dict | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Config:
        from_attributes = True

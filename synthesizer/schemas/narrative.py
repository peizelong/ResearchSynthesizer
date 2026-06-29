from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NarrativeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    article_id: str
    main_themes: list[str] = []
    background: str | None = None
    catalysts: list[str] = []
    industry_segments: list[str] = []
    companies: list[str] = []
    logic_chains: list[str] = []
    angle: str | None = None
    sentiment: str | None = None
    time_window: str | None = None
    extractor_model: str | None = None
    extracted_at: datetime | None = None

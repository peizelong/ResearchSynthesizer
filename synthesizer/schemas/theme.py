from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CompanyMapping(BaseModel):
    name: str
    direction: str = ""
    article_ids: list[str] = []


class ThemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    theme_label: str
    sub_directions: list[str] = []
    article_ids: list[str] = []
    article_angles: dict[str, str] = {}
    consensus: str | None = None
    combined_logic_chain: str | None = None
    upstream: list[str] = []
    midstream: list[str] = []
    downstream: list[str] = []
    companies: list[dict] = []
    divergence_points: list[str] = []
    catalysts: list[str] = []
    member_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ThemeDetailResponse(ThemeResponse):
    """详细视图，可附加关联文章标题等扩展字段。"""
    pass

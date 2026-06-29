from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from synthesizer.radar import radar_controller
from synthesizer.schemas import BatchResponse, ThemeResponse

router = APIRouter(prefix="/api/radar", tags=["radar"])


class RadarConfigRequest(BaseModel):
    interval_seconds: int | None = Field(default=None, ge=60)
    window_hours: int | None = Field(default=None, ge=1)
    article_limit: int | None = Field(default=None, ge=1, le=500)
    crawl_enabled: bool | None = None
    crawl_pages: int | None = Field(default=None, ge=1, le=50)
    crawl_sections: list[str] | None = None
    crawl_sorts: list[str] | None = None
    fetch_details: bool | None = None

    def clean(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


@router.get("/status")
def radar_status():
    """自动叙事流状态。"""
    return radar_controller.status()


@router.get("/latest")
def radar_latest():
    """最新自动融合结果。"""
    data = radar_controller.latest()
    batch = data.get("batch")
    themes = data.get("themes") or []
    data["batch"] = BatchResponse.model_validate(batch).model_dump(mode="json") if batch else None
    data["themes"] = [
        ThemeResponse.model_validate(theme).model_dump(mode="json")
        for theme in themes
    ]
    return data


@router.post("/start")
def radar_start(request: RadarConfigRequest | None = None):
    """启动自动叙事流。"""
    return radar_controller.start(request.clean() if request else None)


@router.post("/stop")
def radar_stop():
    """停止自动叙事流。"""
    return radar_controller.stop()


@router.post("/refresh")
def radar_refresh(request: RadarConfigRequest | None = None):
    """触发一次立即刷新。"""
    return radar_controller.refresh(request.clean() if request else None)

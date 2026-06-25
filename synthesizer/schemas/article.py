from datetime import datetime
from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: str
    source: str
    source_article_id: str | None = None
    url: str
    title: str
    content: str
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    crawled_at: datetime
    trust_level: str
    extraction_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleListItem(BaseModel):
    id: str
    source: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    trust_level: str
    extraction_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlRequest(BaseModel):
    source: str = "jiuyan_web"
    mode: str = "incremental"
    pages: int = Field(default=2, ge=1, le=50)
    sections: list[str] | None = None
    sorts: list[str] | None = None
    fetch_details: bool = True

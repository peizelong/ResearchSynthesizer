"""爬虫基类与公共数据结构。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ArticleMeta:
    """文章列表项元数据（列表页 250 字预览）。"""

    article_id: str
    title: str
    content: str  # 250 字预览
    url: str
    nickname: str | None = None
    create_time: str | None = None
    section: str | None = None
    stock_list: list | None = None


@dataclass
class ArticleDetail:
    """文章详情（详情页完整正文）。"""

    article_id: str
    title: str
    content_html: str
    content_text: str
    stock_list: list | None = None


class BaseCrawler(ABC):
    """爬虫抽象基类。"""

    source: str

    @abstractmethod
    def crawl_list(self, mode: str = "incremental", pages: int = 2, **kwargs) -> list[ArticleMeta]:
        """爬取文章列表，返回 ArticleMeta 列表。"""

    @abstractmethod
    def fetch_detail(self, article_id: str) -> ArticleDetail | None:
        """抓取单篇文章详情，返回 ArticleDetail 或 None。"""

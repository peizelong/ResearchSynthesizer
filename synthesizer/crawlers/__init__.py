"""Narrative Synthesizer 爬虫模块。

提供韭研公社网页端爬虫与爬虫控制器。
"""
from synthesizer.crawlers.base import ArticleDetail, ArticleMeta, BaseCrawler
from synthesizer.crawlers.control import (
    CrawlerAlreadyRunningError,
    CrawlerController,
    crawler_controller,
)
from synthesizer.crawlers.jiuyan_web import JiuyanWebCrawler

__all__ = [
    "ArticleDetail",
    "ArticleMeta",
    "BaseCrawler",
    "CrawlerAlreadyRunningError",
    "CrawlerController",
    "JiuyanWebCrawler",
    "crawler_controller",
]

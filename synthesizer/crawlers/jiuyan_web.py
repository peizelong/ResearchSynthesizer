"""韭研公社网页端爬虫。

通过网页端 SSR 页面抓取文章，无需移动 API 鉴权。

数据来源：
  - 列表页: https://www.jiuyangongshe.com/{section}_{sort}
    section: study / square
    sort:    publish / hot
  - 详情页: https://www.jiuyangongshe.com/a/{article_id}

列表页 __NUXT__ 中 content 为 250 字符预览；
详情页 __NUXT__ 中 content 为完整 HTML 富文本。
"""
from __future__ import annotations

import logging
import random
import re
import threading
import time
from datetime import datetime
from html.parser import HTMLParser
from uuid import uuid4

import requests

from synthesizer.crawlers.base import ArticleDetail, ArticleMeta, BaseCrawler

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jiuyangongshe.com"

# 网页端请求间隔（秒），礼貌抓取
REQUEST_DELAY_MIN = 3
REQUEST_DELAY_MAX = 8
PAGE_TIMEOUT = 20
MAX_RETRIES = 3

# 板块与排序
WEB_SECTIONS = {"study": "研选", "square": "广场"}
WEB_SORTS = {"publish": "最新发布", "hot": "最新热度"}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}


class _HTMLTextExtractor(HTMLParser):
    """从 HTML 中提取纯文本，跳过 script/style/noscript。"""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html: str) -> str:
    """将 HTML 转为纯文本。"""
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def _unescape_nuxt(s: str) -> str:
    """还原 __NUXT__ 字符串中的 \\uXXXX 与转义字符。"""
    if not s:
        return s
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace("\\/", "/").replace("\\n", "\n").replace("\\t", "\t")
    s = s.replace('\\"', '"').replace("\\\\", "\\")
    return s


def _random_delay() -> None:
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))


class JiuyanWebCrawler(BaseCrawler):
    """韭研公社网页端爬虫。"""

    source = "jiuyan_web"

    def __init__(self):
        self._stop_event = threading.Event()
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # 网页请求（带重试）
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str) -> str | None:
        """请求网页，返回 HTML 文本。失败重试 MAX_RETRIES 次。"""
        for attempt in range(MAX_RETRIES):
            if self._stop_event.is_set():
                return None
            try:
                resp = self.session.get(url, timeout=PAGE_TIMEOUT)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except requests.RequestException as e:
                logger.warning(
                    "请求失败（第 %d/%d 次）: %s - %s",
                    attempt + 1, MAX_RETRIES, url, e,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 * (attempt + 1))
        return None

    # ------------------------------------------------------------------
    # __NUXT__ 解析
    # ------------------------------------------------------------------

    def _extract_articles_from_nuxt(self, html: str, section: str) -> list[ArticleMeta]:
        """从列表页 HTML 的 __NUXT__ 中提取文章列表。

        定位 Nuxt 起点 → 按 article_id 切块 → 用正则提取各字段。
        """
        nuxt_match = re.search(
            r"window\.__NUXT__\s*=\s*\(function\([^)]*\)\{return\s*", html
        )
        if not nuxt_match:
            logger.warning("未找到 __NUXT__ 数据")
            return []

        nuxt_str = html[nuxt_match.end():]
        # 按 article_id 切块
        article_blocks = re.split(r'\{article_id:"', nuxt_str)
        metas: list[ArticleMeta] = []

        for block in article_blocks[1:]:
            aid_match = re.match(r'([^"]+)"', block)
            if not aid_match:
                continue
            article_id = aid_match.group(1)

            def get_str(field: str) -> str:
                m = re.search(field + r':"((?:[^"\\]|\\.)*)"', block)
                return _unescape_nuxt(m.group(1)) if m else ""

            title = get_str("title")
            if not title:
                continue

            content = get_str("content")
            create_time = get_str("create_time")
            nickname = get_str("nickname")

            stocks = []
            for sm in re.finditer(
                r'\{stock_id:"([^"]*)",name:"([^"]*)",code:"([^"]*)"\}', block
            ):
                stocks.append({
                    "stock_id": sm.group(1),
                    "name": sm.group(2),
                    "code": sm.group(3),
                })

            metas.append(ArticleMeta(
                article_id=article_id,
                title=title,
                content=content,
                url=f"{BASE_URL}/a/{article_id}",
                nickname=nickname or None,
                create_time=create_time or None,
                section=section,
                stock_list=stocks or None,
            ))

        return metas

    def _extract_detail_from_nuxt(self, html: str, article_id: str) -> ArticleDetail | None:
        """从详情页 __NUXT__ 中提取完整文章内容。

        详情页只有一篇文章，直接取第一个 content 字段（完整 HTML）。
        """
        nuxt_match = re.search(
            r"window\.__NUXT__\s*=\s*\(function\([^)]*\)\{return\s*", html
        )
        if not nuxt_match:
            return None

        nuxt_str = html[nuxt_match.end():]

        content_match = re.search(r'content:"((?:[^"\\]|\\.)*)"', nuxt_str)
        if not content_match:
            return None

        raw_content = content_match.group(1)
        full_html = _unescape_nuxt(raw_content)
        plain_text = html_to_text(full_html)

        title_match = re.search(r'title:"((?:[^"\\]|\\.)*)"', nuxt_str)
        title = _unescape_nuxt(title_match.group(1)) if title_match else ""

        stocks = []
        for sm in re.finditer(
            r'\{stock_id:"([^"]*)",name:"([^"]*)",code:"([^"]*)"\}', nuxt_str
        ):
            stocks.append({
                "stock_id": sm.group(1),
                "name": sm.group(2),
                "code": sm.group(3),
            })

        return ArticleDetail(
            article_id=article_id,
            title=title,
            content_html=full_html,
            content_text=plain_text,
            stock_list=stocks or None,
        )

    # ------------------------------------------------------------------
    # 抽象方法实现
    # ------------------------------------------------------------------

    def crawl_list(self, mode: str = "incremental", pages: int = 2, **kwargs) -> list[ArticleMeta]:
        """爬取文章列表，返回 ArticleMeta 列表。"""
        return self.crawl_incremental(
            sections=kwargs.get("sections"),
            sorts=kwargs.get("sorts"),
            fetch_details=kwargs.get("fetch_details", False),
            max_pages=pages,
        )

    def fetch_detail(self, article_id: str) -> ArticleDetail | None:
        """抓取单篇文章详情页，返回 ArticleDetail 或 None。"""
        url = f"{BASE_URL}/a/{article_id}"
        logger.info("爬取详情: %s", article_id)
        html = self._fetch_page(url)
        if not html:
            return None
        detail = self._extract_detail_from_nuxt(html, article_id)
        if not detail:
            logger.warning("详情页解析失败: %s", article_id)
        return detail

    # ------------------------------------------------------------------
    # 爬取逻辑
    # ------------------------------------------------------------------

    def crawl_list_page(self, section: str = "study", sort: str = "publish") -> list[ArticleMeta]:
        """爬取单个列表页，返回文章元数据列表（含 250 字预览）。"""
        url = f"{BASE_URL}/{section}_{sort}"
        logger.info("爬取列表页: %s", url)
        html = self._fetch_page(url)
        if not html:
            logger.warning("列表页请求失败: %s", url)
            return []
        metas = self._extract_articles_from_nuxt(html, section)
        logger.info("列表页 %s_%s: 提取到 %d 篇文章", section, sort, len(metas))
        return metas

    def crawl_incremental(
        self,
        sections: list[str] | None = None,
        sorts: list[str] | None = None,
        fetch_details: bool = True,
        max_pages: int = 1,
    ) -> list[ArticleMeta]:
        """增量爬取：列表页 → （可选）详情页补全。

        Args:
            sections: 要爬的板块列表，默认 ["study", "square"]
            sorts: 要爬的排序列表，默认 ["publish"]
            fetch_details: 是否爬取详情页（完整正文）
            max_pages: 每个板块+排序组合爬几页

        Returns:
            ArticleMeta 列表（fetch_details=True 时 content 已替换为完整正文）
        """
        sections = sections or ["study", "square"]
        sorts = sorts or ["publish"]
        all_metas: list[ArticleMeta] = []

        for section in sections:
            if self._stop_event.is_set():
                break
            for sort in sorts:
                if self._stop_event.is_set():
                    break

                metas = self.crawl_list_page(section, sort)
                if not metas:
                    continue

                for meta in metas:
                    if self._stop_event.is_set():
                        break
                    all_metas.append(meta)

                    if fetch_details:
                        detail = self.fetch_detail(meta.article_id)
                        if detail:
                            meta.content = detail.content_text
                            if detail.stock_list:
                                meta.stock_list = detail.stock_list
                            logger.info(
                                "详情已获取: [%s] 内容长度: %d 字符",
                                meta.article_id, len(detail.content_text),
                            )
                        _random_delay()

                if self._stop_event.is_set():
                    break
                _random_delay()

        logger.info("增量爬取完成: 共 %d 篇文章", len(all_metas))
        return all_metas

    # ------------------------------------------------------------------
    # 数据库写入
    # ------------------------------------------------------------------

    def save_articles(self, metas: list[ArticleMeta], db) -> int:
        """把爬取结果写入 Article 表。

        INSERT OR REPLACE 逻辑：按 source + source_article_id 去重，
        已存在则更新，不存在则插入（id 用 uuid4 生成）。

        Args:
            metas: ArticleMeta 列表
            db: SQLAlchemy Session

        Returns:
            新插入的文章数量
        """
        from synthesizer.models import Article

        inserted = 0
        for meta in metas:
            if self._stop_event.is_set():
                break

            published_at = self._parse_create_time(meta.create_time)
            now = datetime.utcnow()

            existing = db.query(Article).filter(
                Article.source == self.source,
                Article.source_article_id == meta.article_id,
            ).first()

            if existing:
                existing.title = meta.title
                existing.content = meta.content
                existing.url = meta.url
                existing.author = meta.nickname
                if published_at is not None:
                    existing.published_at = published_at
                existing.crawled_at = now
            else:
                article = Article(
                    id=str(uuid4()),
                    source=self.source,
                    source_article_id=meta.article_id,
                    url=meta.url,
                    title=meta.title,
                    content=meta.content,
                    author=meta.nickname,
                    published_at=published_at,
                    crawled_at=now,
                    trust_level="C",
                    extraction_status="pending",
                    created_at=now,
                )
                db.add(article)
                inserted += 1

        db.commit()
        logger.info("入库完成: 新增 %d / 共 %d 篇", inserted, len(metas))
        return inserted

    @staticmethod
    def _parse_create_time(create_time: str | None):
        """把 create_time 字符串解析为 datetime，失败返回 None。"""
        if not create_time:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(create_time, fmt)
            except ValueError:
                continue
        return None

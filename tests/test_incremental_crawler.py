from __future__ import annotations

from uuid import uuid4

from synthesizer.crawlers.base import ArticleDetail, ArticleMeta
from synthesizer.crawlers.jiuyan_web import JiuyanWebCrawler
from synthesizer.models import Article


class FakeJiuyanCrawler(JiuyanWebCrawler):
    def __init__(self, metas: list[ArticleMeta]):
        super().__init__()
        self._metas = metas
        self.detail_calls: list[str] = []

    def crawl_list_page(self, section: str = "study", sort: str = "publish") -> list[ArticleMeta]:
        return list(self._metas)

    def fetch_detail(self, article_id: str) -> ArticleDetail | None:
        self.detail_calls.append(article_id)
        return ArticleDetail(
            article_id=article_id,
            title=f"title-{article_id}",
            content_html=f"<p>detail-{article_id}</p>",
            content_text=f"detail-{article_id}",
        )


def _meta(article_id: str, title: str | None = None) -> ArticleMeta:
    return ArticleMeta(
        article_id=article_id,
        title=title or f"title-{article_id}",
        content=f"preview-{article_id}",
        url=f"https://example.com/a/{article_id}",
    )


def test_incremental_crawl_skips_existing_before_fetching_detail(monkeypatch):
    monkeypatch.setattr("synthesizer.crawlers.jiuyan_web._random_delay", lambda: None)
    crawler = FakeJiuyanCrawler([_meta("old"), _meta("new"), _meta("new")])

    metas = crawler.crawl_incremental(
        sections=["study"],
        sorts=["publish"],
        fetch_details=True,
        existing_article_ids={"old"},
    )

    assert [m.article_id for m in metas] == ["new"]
    assert crawler.detail_calls == ["new"]
    assert metas[0].content == "detail-new"


def test_save_articles_only_inserts_new_rows(db_session):
    existing = Article(
        id=str(uuid4()),
        source="jiuyan_web",
        source_article_id="old",
        url="https://example.com/a/old",
        title="old-title",
        content="old-content",
        trust_level="C",
        extraction_status="done",
    )
    db_session.add(existing)
    db_session.commit()

    crawler = JiuyanWebCrawler()
    inserted = crawler.save_articles([
        _meta("old", title="changed-title"),
        _meta("new", title="new-title"),
    ], db_session)

    assert inserted == 1
    rows = db_session.query(Article).filter(Article.source == "jiuyan_web").all()
    assert len(rows) == 2
    db_session.refresh(existing)
    assert existing.title == "old-title"
    assert existing.content == "old-content"

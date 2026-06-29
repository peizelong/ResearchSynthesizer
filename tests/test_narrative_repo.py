from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from synthesizer.models import Article, ArticleNarrative
from synthesizer.repositories import NarrativeRepository


def _make_article(db_session) -> Article:
    a = Article(
        id=str(uuid4()),
        source="jiuyan_web",
        source_article_id="n1",
        url="https://example.com/n/1",
        title="叙事测试文章",
        content="正文",
        crawled_at=datetime.utcnow(),
        trust_level="B",
        extraction_status="pending",
    )
    db_session.add(a)
    db_session.commit()
    return a


class TestNarrativeRepository:
    def test_create_and_get(self, db_session):
        article = _make_article(db_session)
        repo = NarrativeRepository(db_session)
        n = repo.create(
            article_id=article.id,
            main_themes=["固态电池安全", "隔膜材料升级"],
            background="电池安全事故频发",
            catalysts=["政策推动", "新技术量产"],
            industry_segments=["隔膜", "阻燃材料"],
            companies=["公司A", "公司B"],
            logic_chains=["安全要求提升 → 隔膜需求增加"],
            angle="从材料升级角度切入",
            sentiment="乐观",
            time_window="2026年下半年",
            extractor_model="demo",
        )
        assert n.id
        assert n.main_themes == ["固态电池安全", "隔膜材料升级"]
        fetched = repo.get(n.id)
        assert fetched is not None
        assert fetched.companies == ["公司A", "公司B"]

    def test_list_by_article_ids(self, db_session):
        article = _make_article(db_session)
        repo = NarrativeRepository(db_session)
        repo.create(article_id=article.id, main_themes=["t1"])
        repo.create(article_id=article.id, main_themes=["t2"])
        result = repo.list_by_article_ids([article.id])
        assert len(result) == 2

    def test_list_by_batch(self, db_session):
        article = _make_article(db_session)
        from synthesizer.models import ResearchBatch
        batch = ResearchBatch(
            id=str(uuid4()),
            name="b",
            article_ids=[article.id],
            status="pending",
            created_at=datetime.utcnow(),
        )
        db_session.add(batch)
        db_session.commit()
        repo = NarrativeRepository(db_session)
        repo.create(article_id=article.id, main_themes=["t1"])
        result = repo.list_by_batch(batch)
        assert len(result) == 1

    def test_list_by_article_ids_empty(self, db_session):
        repo = NarrativeRepository(db_session)
        assert repo.list_by_article_ids([]) == []

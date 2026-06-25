"""测试公共 fixtures。"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 在导入应用代码前覆盖 DATABASE_URL，避免触及开发库
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"

from synthesizer.database import Base  # noqa: E402
from synthesizer.models import Article, Claim, ResearchBatch  # noqa: E402


@pytest.fixture()
def db_session():
    """创建一个隔离的内存/临时 SQLite 数据库并返回 Session。"""
    engine = create_engine(
        f"sqlite:///{_tmp_db.name}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def sample_articles(db_session) -> list[Article]:
    """创建 3 篇示例文章。"""
    now = datetime.utcnow()
    articles = []
    for i in range(3):
        a = Article(
            id=str(uuid4()),
            source="jiuyan_web",
            source_article_id=f"jy_{i}",
            url=f"https://example.com/a/{i}",
            title=f"示例文章 {i}",
            content=f"文章 {i} 的正文内容。",
            crawled_at=now,
            trust_level="B",
            extraction_status="done",
        )
        db_session.add(a)
        articles.append(a)
    db_session.commit()
    return articles


@pytest.fixture()
def sample_batch(db_session, sample_articles) -> ResearchBatch:
    batch = ResearchBatch(
        id=str(uuid4()),
        name="测试批次",
        article_ids=[a.id for a in sample_articles],
        status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add(batch)
    db_session.commit()
    return batch


def make_claim(
    article_id: str,
    direction_tag: str | None,
    direction_angle: str | None = "industry",
    confidence: float = 0.7,
    subject: str = "示例主体",
    predicate: str = "示例谓词",
) -> dict:
    """构造 claim dict，方便测试。"""
    return {
        "id": str(uuid4()),
        "article_id": article_id,
        "claim_type": "direction",
        "subject": subject,
        "predicate": predicate,
        "direction_tag": direction_tag,
        "direction_angle": direction_angle,
        "evidence_text": "示例证据。",
        "confidence": confidence,
    }

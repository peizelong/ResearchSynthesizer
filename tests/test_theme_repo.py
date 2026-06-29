from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from synthesizer.models import ResearchBatch
from synthesizer.repositories import ThemeRepository


def _make_batch(db_session) -> ResearchBatch:
    batch = ResearchBatch(
        id=str(uuid4()),
        name="tb",
        article_ids=[str(uuid4())],
        status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add(batch)
    db_session.commit()
    return batch


class TestThemeRepository:
    def test_create_and_get(self, db_session):
        batch = _make_batch(db_session)
        repo = ThemeRepository(db_session)
        t = repo.create(
            batch_id=batch.id,
            theme_label="电池安全材料升级",
            sub_directions=["隔膜", "阻燃材料"],
            article_ids=batch.article_ids,
            member_count=2,
        )
        assert t.id
        assert t.theme_label == "电池安全材料升级"
        assert repo.get(t.id).theme_label == "电池安全材料升级"

    def test_update_partial_fields(self, db_session):
        batch = _make_batch(db_session)
        repo = ThemeRepository(db_session)
        t = repo.create(batch_id=batch.id, theme_label="t", article_ids=[], member_count=1)
        updated = repo.update(
            t.id,
            consensus="多文共识XXX",
            combined_logic_chain="A → B → C",
            upstream=["基础化工材料"],
        )
        assert updated.consensus == "多文共识XXX"
        assert updated.upstream == ["基础化工材料"]

    def test_list_by_batch(self, db_session):
        batch = _make_batch(db_session)
        repo = ThemeRepository(db_session)
        repo.create(batch_id=batch.id, theme_label="t1", article_ids=[], member_count=3)
        repo.create(batch_id=batch.id, theme_label="t2", article_ids=[], member_count=1)
        result = repo.list_by_batch(batch.id)
        assert len(result) == 2
        # member_count 降序
        assert result[0].member_count >= result[1].member_count

    def test_delete_by_batch(self, db_session):
        batch = _make_batch(db_session)
        repo = ThemeRepository(db_session)
        repo.create(batch_id=batch.id, theme_label="t1", article_ids=[], member_count=1)
        repo.create(batch_id=batch.id, theme_label="t2", article_ids=[], member_count=1)
        rows = repo.delete_by_batch(batch.id)
        assert rows == 2
        assert repo.list_by_batch(batch.id) == []

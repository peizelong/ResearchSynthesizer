"""聚类器与服务测试。"""
from __future__ import annotations

from synthesizer.clustering.clusterer import (
    normalize_tag,
    rule_based_group,
    compute_angle_distribution,
    compute_source_distribution,
    select_representative,
)
from synthesizer.clustering.service import ClusteringService
from synthesizer.models import Claim
from synthesizer.repositories import ClaimRepository, ClusterRepository
from tests.conftest import make_claim


class TestNormalizeTag:
    def test_normalizes_whitespace_and_case(self):
        assert normalize_tag("HBM 供应紧张") == "hbm供应紧张"

    def test_strips_punctuation(self):
        assert normalize_tag("HBM、供应-紧张！") == "hbm供应紧张"

    def test_none_returns_empty(self):
        assert normalize_tag(None) == ""

    def test_empty_string(self):
        assert normalize_tag("") == ""


class TestRuleBasedGroup:
    def test_groups_by_normalized_tag(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, "HBM供应紧张", confidence=0.8)),
            Claim(**make_claim(sample_articles[1].id, "HBM 供应紧张", confidence=0.7)),
            Claim(**make_claim(sample_articles[2].id, "AI算力需求", confidence=0.6)),
        ]
        db_session.add_all(claims)
        db_session.commit()

        groups = rule_based_group(claims)
        # "HBM供应紧张" 与 "HBM 供应紧张" 标准化后相同
        assert len(groups) == 2
        hbm_key = normalize_tag("HBM供应紧张")
        assert hbm_key in groups
        assert len(groups[hbm_key]) == 2

    def test_empty_tag_goes_to_empty_bucket(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, None)),
        ]
        db_session.add_all(claims)
        db_session.commit()

        groups = rule_based_group(claims)
        assert "" in groups
        assert len(groups[""]) == 1


class TestDistributions:
    def test_angle_distribution(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, "tag1", direction_angle="policy")),
            Claim(**make_claim(sample_articles[1].id, "tag1", direction_angle="industry")),
            Claim(**make_claim(sample_articles[2].id, "tag1", direction_angle="policy")),
        ]
        db_session.add_all(claims)
        db_session.commit()

        dist = compute_angle_distribution(claims)
        assert dist == {"policy": 2, "industry": 1}

    def test_source_distribution(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, "tag1")),
            Claim(**make_claim(sample_articles[1].id, "tag1")),
            Claim(**make_claim(sample_articles[2].id, "tag1")),
        ]
        db_session.add_all(claims)
        db_session.commit()

        dist = compute_source_distribution(claims)
        # 三篇文章均来自 jiuyan_web
        assert dist == {"jiuyan_web": 3}

    def test_angle_distribution_handles_none(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, "tag1", direction_angle=None)),
        ]
        db_session.add_all(claims)
        db_session.commit()

        dist = compute_angle_distribution(claims)
        assert dist == {"unknown": 1}


class TestSelectRepresentative:
    def test_returns_highest_confidence_id(self, db_session, sample_articles):
        claims = [
            Claim(**make_claim(sample_articles[0].id, "tag1", confidence=0.6)),
            Claim(**make_claim(sample_articles[1].id, "tag1", confidence=0.9)),
            Claim(**make_claim(sample_articles[2].id, "tag1", confidence=0.7)),
        ]
        db_session.add_all(claims)
        db_session.commit()

        rep_id = select_representative(claims)
        assert rep_id == claims[1].id

    def test_empty_returns_none(self):
        assert select_representative([]) is None


class TestClusteringService:
    def test_cluster_batch_creates_clusters(self, db_session, sample_batch, sample_articles):
        """3 篇文章共 5 条 claims，按 tag 应形成 3 个聚类。"""
        claim_repo = ClaimRepository(db_session)
        # HBM供应紧张 × 2（同一聚类，达到 MIN_CLUSTER_SIZE=2）
        # AI算力需求 × 2
        # 半导体国产替代 × 1（孤立）
        claim_repo.bulk_create([
            make_claim(sample_articles[0].id, "HBM供应紧张", direction_angle="industry", confidence=0.8),
            make_claim(sample_articles[1].id, "HBM 供应紧张", direction_angle="policy", confidence=0.7),
            make_claim(sample_articles[0].id, "AI算力需求", direction_angle="industry", confidence=0.75),
            make_claim(sample_articles[2].id, "AI算力需求", direction_angle="tech", confidence=0.65),
            make_claim(sample_articles[1].id, "半导体国产替代", direction_angle="policy", confidence=0.6),
        ])

        service = ClusteringService(db_session)
        clusters = service.cluster_batch(sample_batch.id)

        # 3 个聚类
        assert len(clusters) == 3
        labels = {c.cluster_label for c in clusters}
        # label 取自 group 内首条 claim，顺序不保证；用 normalize 比较
        normalized_labels = {normalize_tag(lbl) for lbl in labels}
        assert "hbm供应紧张" in normalized_labels
        assert "ai算力需求" in normalized_labels
        # 半导体国产替代只有 1 条，应该被标记为孤立
        assert any("[孤立]" in lbl for lbl in labels)

        # 每个聚类的成员数累加 == 5
        total_members = sum(c.member_count for c in clusters)
        assert total_members == 5

    def test_cluster_batch_assigns_cluster_id_to_claims(
        self, db_session, sample_batch, sample_articles
    ):
        claim_repo = ClaimRepository(db_session)
        cluster_repo = ClusterRepository(db_session)

        claim_repo.bulk_create([
            make_claim(sample_articles[0].id, "HBM供应紧张"),
            make_claim(sample_articles[1].id, "HBM供应紧张"),
        ])

        service = ClusteringService(db_session)
        clusters = service.cluster_batch(sample_batch.id)

        assert len(clusters) == 1
        cluster = clusters[0]
        # 验证 claims 已回填
        claims_in_cluster = cluster_repo.get_claims(cluster.id)
        assert len(claims_in_cluster) == 2
        for c in claims_in_cluster:
            assert c.topic_cluster_id == cluster.id

    def test_cluster_batch_empty_claims_returns_empty(
        self, db_session, sample_batch
    ):
        """批次无 claims 时返回空列表，状态置为 completed。"""
        service = ClusteringService(db_session)
        clusters = service.cluster_batch(sample_batch.id)
        assert clusters == []

    def test_cluster_batch_records_angle_distribution(
        self, db_session, sample_batch, sample_articles
    ):
        claim_repo = ClaimRepository(db_session)
        claim_repo.bulk_create([
            make_claim(sample_articles[0].id, "tag1", direction_angle="policy"),
            make_claim(sample_articles[1].id, "tag1", direction_angle="industry"),
            make_claim(sample_articles[2].id, "tag1", direction_angle="policy"),
        ])

        service = ClusteringService(db_session)
        clusters = service.cluster_batch(sample_batch.id)

        assert len(clusters) == 1
        cluster = clusters[0]
        assert cluster.angle_distribution == {"policy": 2, "industry": 1}
        assert cluster.article_count == 3

    def test_cluster_batch_unknown_batch_raises(self, db_session):
        service = ClusteringService(db_session)
        try:
            service.cluster_batch("non-existent-id")
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "not found" in str(e)

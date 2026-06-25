"""聚类服务 - 编排规则聚类流程"""
import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session

from synthesizer.models import ResearchBatch, TopicCluster, Claim
from synthesizer.repositories import ClaimRepository, ClusterRepository, BatchRepository
from synthesizer.clustering.clusterer import (
    rule_based_group,
    compute_angle_distribution,
    compute_source_distribution,
    select_representative,
    normalize_tag,
)
from synthesizer.config import MIN_CLUSTER_SIZE

logger = logging.getLogger(__name__)


class ClusteringService:
    def __init__(self, db: Session):
        self.db = db
        self.claim_repo = ClaimRepository(db)
        self.cluster_repo = ClusterRepository(db)
        self.batch_repo = BatchRepository(db)

    def cluster_batch(self, batch_id: str) -> list[TopicCluster]:
        """对批次内的 claims 做规则聚类"""
        batch = self.batch_repo.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        self.batch_repo.update_status(batch_id, "clustering", stage="cluster_directions")

        # 加载批次内所有已抽取 claims
        claims = self.claim_repo.list_by_batch(batch)
        if not claims:
            logger.warning(f"No claims found for batch {batch_id}")
            self.batch_repo.update_status(batch_id, "completed", stage="cluster_done")
            return []

        # 规则聚类
        groups = rule_based_group(claims)
        clusters: list[TopicCluster] = []

        for tag_key, group_claims in groups.items():
            if not tag_key:
                # direction_tag 为空的 claims 归为"未分类"
                label = "未分类方向"
            else:
                # 用第一个 claim 的原始 direction_tag 作为标签
                label = group_claims[0].direction_tag or tag_key

            # 小于最小聚类大小的归为孤立方向
            if len(group_claims) < MIN_CLUSTER_SIZE:
                label = f"[孤立] {label}"

            # 选择代表性 claim
            rep_id = select_representative(group_claims)

            # 统计
            angle_dist = compute_angle_distribution(group_claims)
            source_dist = compute_source_distribution(group_claims)
            article_ids = list(set(c.article_id for c in group_claims))

            cluster = self.cluster_repo.create(
                id=str(uuid4()),
                batch_id=batch_id,
                cluster_label=label,
                cluster_summary=None,
                representative_claim_id=rep_id,
                member_count=len(group_claims),
                article_count=len(article_ids),
                angle_distribution=angle_dist,
                source_distribution=source_dist,
                cluster_method="rule",
                created_at=datetime.utcnow(),
            )

            # 回填 claims 的 topic_cluster_id
            claim_ids = [c.id for c in group_claims]
            self.claim_repo.assign_cluster(claim_ids, cluster.id)

            clusters.append(cluster)
            logger.info(f"Cluster '{label}': {len(group_claims)} claims, {len(article_ids)} articles")

        self.batch_repo.update_status(batch_id, "completed", stage="cluster_done")
        logger.info(f"Batch {batch_id}: {len(clusters)} clusters created")
        return clusters

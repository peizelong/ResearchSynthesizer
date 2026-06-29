"""theme_merge_node: 方向融合。

对每个 raw_cluster 调 LLM 生成统一 theme_label / sub_directions / consensus，
创建 MergedTheme 持久化（骨架），并把 MergedThemeData 放入 state.merged_themes。

后续 angle_compare / logic_chain / company_mapping 节点读取 merged_themes
逐步回填字段。
"""
from __future__ import annotations

import logging

from synthesizer.repositories import BatchRepository, ThemeRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import build_merge_prompt
from synthesizer.workflow.state import MergedThemeData, WorkflowState

logger = logging.getLogger(__name__)


def build_theme_merge_node(db, llm: LLMFusionClient | None = None):
    """返回绑定 db 的 theme_merge_node 闭包。"""
    if llm is None:
        llm = LLMFusionClient()

    def theme_merge_node(state: WorkflowState) -> dict:
        batch_repo = BatchRepository(db)
        theme_repo = ThemeRepository(db)

        batch_repo.update_status(state["batch_id"], "running", stage="merge_themes")

        raw_clusters = state.get("raw_clusters", [])
        if not raw_clusters:
            return {"merged_themes": []}

        # 清理同批次旧 merged_themes（重跑时使用）
        theme_repo.delete_by_batch(state["batch_id"])

        merged: list[MergedThemeData] = []
        for cluster in raw_clusters:
            article_ids = cluster.get("article_ids", []) or []
            sub_dirs = cluster.get("sub_directions", []) or []

            # 调 LLM 生成融合主题
            try:
                data = llm.complete_json(
                    system="你是投研主题融合专家。只输出 JSON。",
                    user=build_merge_prompt(cluster),
                )
                theme_label = data.get("theme_label") or cluster.get("theme_label", "未命名主题")
                refined_subs = data.get("sub_directions") or sub_dirs
                consensus = data.get("consensus") or ""
            except Exception as exc:
                logger.exception("theme_merge LLM failed for cluster %s", cluster.get("theme_label"))
                theme_label = cluster.get("theme_label", "未命名主题")
                refined_subs = sub_dirs
                consensus = ""

            # 持久化骨架（angle/logic/company 字段后续回填）
            theme = theme_repo.create(
                batch_id=state["batch_id"],
                theme_label=theme_label,
                sub_directions=refined_subs,
                article_ids=article_ids,
                member_count=len(article_ids),
                # 占位空值
                article_angles={},
                divergence_points=[],
                consensus=consensus or None,
                combined_logic_chain=None,
                upstream=[],
                midstream=[],
                downstream=[],
                companies=[],
                catalysts=[],
            )

            merged.append(MergedThemeData(
                theme_id=theme.id,
                theme_label=theme.theme_label,
                sub_directions=theme.sub_directions,
                article_ids=theme.article_ids,
                member_count=theme.member_count,
                article_angles={},
                divergence_points=[],
                consensus=consensus,
                combined_logic_chain="",
                upstream=[],
                midstream=[],
                downstream=[],
                companies=[],
                catalysts=[],
            ))

        logger.info(
            "theme_merge: batch %s -> %d merged themes",
            state["batch_id"], len(merged),
        )
        return {"merged_themes": merged}

    return theme_merge_node

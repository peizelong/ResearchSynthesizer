"""theme_merge_node: MergedDirection 持久化。

Prompt 2 已经完成方向归一与去重；本节点只把 raw_clusters/MergedDirection
转换为 MergedTheme 持久化，并把 MergedThemeData 放入 state.merged_themes。

后续兼容节点只补齐缺失字段，不再做主判断。
"""
from __future__ import annotations

import logging

from synthesizer.repositories import BatchRepository, ThemeRepository
from synthesizer.services import LLMFusionClient
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
            article_ids = list(dict.fromkeys(cluster.get("article_ids", []) or []))
            refined_subs = list(dict.fromkeys(cluster.get("sub_directions", []) or []))
            theme_label = cluster.get("theme_label", "未命名方向")
            consensus = cluster.get("consensus", "") or ""
            combined_logic_chain = _format_logic_chain(cluster.get("combined_logic_chain", []))
            different_angles = cluster.get("different_angles", []) or []
            industry_segments = list(dict.fromkeys(cluster.get("industry_segments", []) or []))
            companies = cluster.get("companies", []) or []
            catalysts = list(dict.fromkeys(cluster.get("catalysts", []) or []))

            # 持久化骨架（angle/logic/company 字段后续回填）
            theme = theme_repo.create(
                batch_id=state["batch_id"],
                theme_label=theme_label,
                sub_directions=refined_subs,
                article_ids=article_ids,
                member_count=len(article_ids),
                article_angles={},
                divergence_points=different_angles,
                consensus=consensus or None,
                combined_logic_chain=combined_logic_chain or None,
                upstream=[],
                midstream=industry_segments,
                downstream=[],
                companies=companies,
                catalysts=catalysts,
            )

            merged.append(MergedThemeData(
                theme_id=theme.id,
                theme_label=theme.theme_label,
                sub_directions=theme.sub_directions,
                article_ids=theme.article_ids,
                member_count=theme.member_count,
                article_angles={},
                divergence_points=different_angles,
                consensus=consensus,
                combined_logic_chain=combined_logic_chain,
                upstream=[],
                midstream=industry_segments,
                downstream=[],
                companies=companies,
                catalysts=catalysts,
                aliases=cluster.get("raw_themes", []) or [],
                source_unit_ids=cluster.get("source_unit_ids", []) or [],
                related_directions=cluster.get("related_directions", []) or [],
                merge_reason=cluster.get("merge_reason", "") or "",
            ))

        logger.info(
            "theme_merge: batch %s -> %d merged themes",
            state["batch_id"], len(merged),
        )
        return {"merged_themes": merged}

    return theme_merge_node


def _format_logic_chain(value) -> str:
    if isinstance(value, list):
        return " → ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip()
    return ""

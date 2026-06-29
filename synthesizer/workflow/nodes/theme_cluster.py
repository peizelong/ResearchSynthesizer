"""theme_cluster_node: 主题聚类。

把 state.narratives 里所有 main_themes 喂给 LLM 做语义聚类，产出 raw_clusters。
不写 db（合并后由 theme_merge_node 写 MergedTheme）。

LLM 不可用或返回空时退化为按 main_themes 字面值分组（保证流程不中断）。
"""
from __future__ import annotations

import logging
from collections import defaultdict

from synthesizer.repositories import BatchRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import build_cluster_prompt
from synthesizer.workflow.state import RawCluster, WorkflowState

logger = logging.getLogger(__name__)


def build_theme_cluster_node(db, llm: LLMFusionClient | None = None):
    """返回绑定 db 的 theme_cluster_node 闭包。"""
    if llm is None:
        llm = LLMFusionClient()

    def theme_cluster_node(state: WorkflowState) -> dict:
        batch_repo = BatchRepository(db)
        # 容错：批次可能不存在（如纯单元测试用假 batch_id），不应阻断聚类逻辑
        try:
            batch_repo.update_status(state["batch_id"], "running", stage="cluster_themes")
        except Exception:
            logger.debug("theme_cluster: skip batch status update for %s", state.get("batch_id"))

        narratives = state.get("narratives", [])
        if not narratives:
            logger.warning("theme_cluster: no narratives in state")
            return {"raw_clusters": []}

        # 构造 LLM 输入
        article_themes = [
            {"article_id": n["article_id"], "main_themes": n["main_themes"]}
            for n in narratives
        ]

        raw_clusters: list[RawCluster] = []
        errors: list[str] = []

        try:
            prompt = build_cluster_prompt(article_themes)
            data = llm.complete_json(
                system="你是投研主题聚类专家。只输出 JSON。",
                user=prompt,
            )
            clusters = data.get("clusters", []) if isinstance(data, dict) else []
            for c in clusters:
                raw_clusters.append(RawCluster(
                    theme_label=c.get("theme_label", "未命名主题"),
                    sub_directions=c.get("sub_directions", []) or [],
                    article_ids=c.get("article_ids", []) or [],
                    raw_themes=c.get("raw_themes", []) or [],
                ))
        except Exception as exc:
            logger.exception("theme_cluster LLM call failed, fallback to literal grouping")
            errors.append(f"theme_cluster: {exc}")

        # 兜底：LLM 失败或返回空时按字面 main_themes 分组
        if not raw_clusters:
            raw_clusters = _literal_grouping(narratives)

        logger.info(
            "theme_cluster: batch %s -> %d raw clusters",
            state["batch_id"], len(raw_clusters),
        )
        result: dict = {"raw_clusters": raw_clusters}
        if errors:
            result["errors"] = errors
        return result

    return theme_cluster_node


def _literal_grouping(narratives: list[dict]) -> list[RawCluster]:
    """兜底聚类：按 main_themes 字面值分组。"""
    groups: dict[str, list[str]] = defaultdict(list)  # theme -> article_ids
    for n in narratives:
        for theme in n.get("main_themes", []):
            groups[theme].append(n["article_id"])

    clusters: list[RawCluster] = []
    for theme, article_ids in groups.items():
        clusters.append(RawCluster(
            theme_label=theme,
            sub_directions=[theme],
            article_ids=list(set(article_ids)),
            raw_themes=[theme],
        ))
    return clusters

"""theme_cluster_node: 多文方向归一与去重。

把 state.narratives 里的 NarrativeUnit 喂给 LLM 做方向归一与去重，产出 raw_clusters。
不写 db（合并后由 theme_merge_node 写 MergedTheme）。

LLM 不可用或返回空时退化为按 direction 字面值分组（保证流程不中断）。
"""
from __future__ import annotations

import logging
from collections import defaultdict

from synthesizer.repositories import BatchRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import DIRECTION_MERGE_SYSTEM, build_direction_merge_prompt
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

        narrative_units = [_to_unit_payload(n) for n in narratives]

        raw_clusters: list[RawCluster] = []
        errors: list[str] = []
        not_merged: list[dict] = []

        try:
            data = llm.complete_json(
                system=DIRECTION_MERGE_SYSTEM,
                user=build_direction_merge_prompt(narrative_units),
            )
            directions = data.get("merged_directions", []) if isinstance(data, dict) else []
            not_merged = data.get("not_merged", []) if isinstance(data, dict) else []
            for direction in directions:
                raw_clusters.append(_direction_to_raw_cluster(direction))
        except Exception as exc:
            logger.exception("direction_merge LLM call failed, fallback to literal grouping")
            errors.append(f"theme_cluster: {exc}")

        # 兜底：LLM 失败或返回空时按字面 direction 分组
        if not raw_clusters:
            raw_clusters = _literal_grouping(narratives)

        logger.info(
            "theme_cluster: batch %s -> %d raw clusters",
            state["batch_id"], len(raw_clusters),
        )
        result: dict = {"raw_clusters": raw_clusters, "not_merged": not_merged}
        if errors:
            result["errors"] = errors
        return result

    return theme_cluster_node


def _to_unit_payload(n: dict) -> dict:
    themes = n.get("main_themes", []) or []
    direction = n.get("direction") or (themes[0] if themes else "")
    sub_direction = n.get("sub_direction") or (themes[1] if len(themes) > 1 else "")
    return {
        "unit_id": n.get("narrative_id"),
        "article_id": n.get("article_id"),
        "direction": direction,
        "sub_direction": sub_direction,
        "unit_type": n.get("unit_type", "other"),
        "angle": n.get("angle", ""),
        "logic_chain": n.get("logic_chain") or n.get("logic_chains", []),
        "catalysts": n.get("catalysts", []),
        "industry_segments": n.get("industry_segments", []),
        "companies": n.get("companies", []),
        "source_quotes": n.get("source_quotes", []),
        "importance": n.get("importance", "core"),
    }


def _direction_to_raw_cluster(direction: dict) -> RawCluster:
    source_article_ids = direction.get("source_article_ids", direction.get("article_ids", [])) or []
    aliases = direction.get("aliases", direction.get("raw_themes", [])) or []
    direction_name = direction.get("direction_name") or direction.get("theme_label") or "未命名方向"
    return RawCluster(
        theme_label=direction_name,
        sub_directions=direction.get("sub_directions", []) or [],
        article_ids=list(dict.fromkeys(source_article_ids)),
        raw_themes=aliases,
        source_unit_ids=direction.get("source_unit_ids", []) or [],
        consensus=direction.get("consensus", "") or "",
        different_angles=direction.get("different_angles", []) or [],
        combined_logic_chain=direction.get("combined_logic_chain", []) or [],
        catalysts=direction.get("catalysts", []) or [],
        industry_segments=direction.get("industry_segments", []) or [],
        companies=direction.get("companies", []) or [],
        related_directions=direction.get("related_directions", []) or [],
        merge_reason=direction.get("merge_reason", "") or "",
    )


def _literal_grouping(narratives: list[dict]) -> list[RawCluster]:
    """兜底聚类：按 direction 字面值分组。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for n in narratives:
        unit = _to_unit_payload(n)
        if n.get("direction") or not n.get("main_themes"):
            directions = [unit.get("direction") or "未命名方向"]
        else:
            directions = [theme for theme in n.get("main_themes", []) if theme]
        for direction in directions:
            grouped_unit = {**unit, "direction": direction}
            groups[direction].append(grouped_unit)

    clusters: list[RawCluster] = []
    for theme, units in groups.items():
        article_ids = [unit["article_id"] for unit in units if unit.get("article_id")]
        source_unit_ids = [unit["unit_id"] for unit in units if unit.get("unit_id")]
        sub_dirs = [unit["sub_direction"] for unit in units if unit.get("sub_direction")]
        clusters.append(RawCluster(
            theme_label=theme,
            sub_directions=list(dict.fromkeys(sub_dirs or [theme])),
            article_ids=list(dict.fromkeys(article_ids)),
            raw_themes=[theme],
            source_unit_ids=list(dict.fromkeys(source_unit_ids)),
            consensus="",
            different_angles=list(dict.fromkeys([unit.get("angle", "") for unit in units if unit.get("angle")])),
            combined_logic_chain=[],
            catalysts=list(dict.fromkeys([x for unit in units for x in unit.get("catalysts", [])])),
            industry_segments=list(dict.fromkeys([x for unit in units for x in unit.get("industry_segments", [])])),
            companies=[company for unit in units for company in unit.get("companies", [])],
            related_directions=[],
            merge_reason="LLM 不可用时按 direction 字面值兜底分组",
        ))
    return clusters

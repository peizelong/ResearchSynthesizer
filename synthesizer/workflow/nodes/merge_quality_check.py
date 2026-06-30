"""merge_quality_check_node: NarrativeUnit -> MergedDirection 质检。"""
from __future__ import annotations

import logging

from synthesizer.repositories import ThemeRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import MERGE_QUALITY_CHECK_SYSTEM, build_merge_quality_check_prompt
from synthesizer.workflow.state import MergedThemeData, WorkflowState

logger = logging.getLogger(__name__)


def build_merge_quality_check_node(db, llm: LLMFusionClient | None = None):
    if llm is None:
        llm = LLMFusionClient()

    def merge_quality_check_node(state: WorkflowState) -> dict:
        narratives = state.get("narratives", []) or []
        merged_themes: list[MergedThemeData] = state.get("merged_themes", []) or []
        if not narratives or not merged_themes:
            return {"quality_issues": []}

        narrative_units = [_narrative_to_unit(n) for n in narratives]
        merged_directions = [_theme_to_direction(theme) for theme in merged_themes]

        try:
            data = llm.complete_json(
                system=MERGE_QUALITY_CHECK_SYSTEM,
                user=build_merge_quality_check_prompt(narrative_units, merged_directions),
            )
        except Exception as exc:
            logger.exception("merge_quality_check LLM failed")
            return {"quality_issues": [{
                "type": "other",
                "description": f"质检调用失败：{exc}",
                "affected_direction": "",
                "suggested_fix": "保留当前聚合结果",
            }]}

        if not isinstance(data, dict):
            return {"quality_issues": []}

        issues = data.get("issues", []) or []
        corrected = data.get("corrected_merged_directions", []) or []
        if not data.get("has_issue") or not corrected:
            return {"quality_issues": issues}

        theme_repo = ThemeRepository(db)
        theme_repo.delete_by_batch(state["batch_id"])
        rebuilt: list[MergedThemeData] = []
        for direction in corrected:
            if not isinstance(direction, dict):
                continue
            theme_data = _create_theme_from_direction(theme_repo, state["batch_id"], direction)
            rebuilt.append(theme_data)

        return {"merged_themes": rebuilt or merged_themes, "quality_issues": issues}

    return merge_quality_check_node


def _narrative_to_unit(n: dict) -> dict:
    themes = n.get("main_themes", []) or []
    return {
        "unit_id": n.get("narrative_id"),
        "article_id": n.get("article_id"),
        "direction": n.get("direction") or (themes[0] if themes else ""),
        "sub_direction": n.get("sub_direction") or (themes[1] if len(themes) > 1 else ""),
        "unit_type": n.get("unit_type", "other"),
        "angle": n.get("angle", ""),
        "logic_chain": n.get("logic_chain") or n.get("logic_chains", []),
        "catalysts": n.get("catalysts", []),
        "industry_segments": n.get("industry_segments", []),
        "companies": n.get("companies", []),
        "source_quotes": n.get("source_quotes", []),
        "importance": n.get("importance", "core"),
    }


def _theme_to_direction(theme: dict) -> dict:
    return {
        "direction_name": theme.get("theme_label", ""),
        "aliases": theme.get("aliases", []) or [],
        "sub_directions": theme.get("sub_directions", []) or [],
        "source_unit_ids": theme.get("source_unit_ids", []) or [],
        "source_article_ids": theme.get("article_ids", []) or [],
        "consensus": theme.get("consensus", "") or "",
        "different_angles": theme.get("divergence_points", []) or [],
        "combined_logic_chain": theme.get("combined_logic_chain", "") or "",
        "catalysts": theme.get("catalysts", []) or [],
        "industry_segments": (
            (theme.get("upstream", []) or [])
            + (theme.get("midstream", []) or [])
            + (theme.get("downstream", []) or [])
        ),
        "companies": theme.get("companies", []) or [],
        "related_directions": theme.get("related_directions", []) or [],
        "merge_reason": theme.get("merge_reason", "") or "",
    }


def _create_theme_from_direction(theme_repo: ThemeRepository, batch_id: str, direction: dict) -> MergedThemeData:
    article_ids = list(dict.fromkeys(direction.get("source_article_ids", []) or []))
    logic_chain = direction.get("combined_logic_chain", [])
    if isinstance(logic_chain, list):
        logic_chain_text = " → ".join(str(x).strip() for x in logic_chain if str(x).strip())
    else:
        logic_chain_text = str(logic_chain or "")

    theme = theme_repo.create(
        batch_id=batch_id,
        theme_label=direction.get("direction_name") or "未命名方向",
        sub_directions=direction.get("sub_directions", []) or [],
        article_ids=article_ids,
        member_count=len(article_ids),
        article_angles={},
        divergence_points=direction.get("different_angles", []) or [],
        consensus=direction.get("consensus") or None,
        combined_logic_chain=logic_chain_text or None,
        upstream=[],
        midstream=direction.get("industry_segments", []) or [],
        downstream=[],
        companies=direction.get("companies", []) or [],
        catalysts=direction.get("catalysts", []) or [],
    )
    return MergedThemeData(
        theme_id=theme.id,
        theme_label=theme.theme_label,
        sub_directions=theme.sub_directions,
        article_ids=theme.article_ids,
        member_count=theme.member_count,
        article_angles={},
        divergence_points=theme.divergence_points,
        consensus=theme.consensus or "",
        combined_logic_chain=theme.combined_logic_chain or "",
        upstream=[],
        midstream=theme.midstream,
        downstream=[],
        companies=theme.companies,
        catalysts=theme.catalysts,
        aliases=direction.get("aliases", []) or [],
        source_unit_ids=direction.get("source_unit_ids", []) or [],
        related_directions=direction.get("related_directions", []) or [],
        merge_reason=direction.get("merge_reason", "") or "",
    )

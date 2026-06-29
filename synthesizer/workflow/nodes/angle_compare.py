"""angle_compare_node: 差异视角比较。

对每个 merged_theme，根据其 article_ids 从 state.narratives 拉取对应文章的
angle / background / logic_chains，调 LLM 比较视角差异，回填：
  - article_angles: {article_id -> angle 一句话}
  - divergence_points: list[str]

回填后更新 db 中的 MergedTheme，并返回完整 merged_themes 列表
（LangGraph 默认 dict 替换语义，必须返回完整列表）。
"""
from __future__ import annotations

import logging

from synthesizer.repositories import ThemeRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import build_angle_prompt
from synthesizer.workflow.state import MergedThemeData, WorkflowState

logger = logging.getLogger(__name__)


def build_angle_compare_node(db, llm: LLMFusionClient | None = None):
    if llm is None:
        llm = LLMFusionClient()

    def angle_compare_node(state: WorkflowState) -> dict:
        theme_repo = ThemeRepository(db)

        merged_themes: list[MergedThemeData] = state.get("merged_themes", [])
        narratives: list[dict] = state.get("narratives", [])
        narratives_by_id = {n["article_id"]: n for n in narratives}

        if not merged_themes:
            return {"merged_themes": []}

        updated: list[MergedThemeData] = []
        for theme in merged_themes:
            article_ids = theme.get("article_ids", []) or []
            articles_for_prompt = []
            for aid in article_ids:
                n = narratives_by_id.get(aid)
                if n:
                    articles_for_prompt.append({
                        "article_id": aid,
                        "angle": n.get("angle", ""),
                        "background": n.get("background", ""),
                        "logic_chains": n.get("logic_chains", []),
                    })

            article_angles: dict[str, str] = {}
            divergence_points: list[str] = []

            if articles_for_prompt:
                try:
                    data = llm.complete_json(
                        system="你是投研视角比较专家。只输出 JSON。",
                        user=build_angle_prompt(theme["theme_label"], articles_for_prompt),
                    )
                    article_angles = data.get("article_angles", {}) or {}
                    divergence_points = data.get("divergence_points", []) or []
                except Exception as exc:
                    logger.exception("angle_compare LLM failed for theme %s", theme.get("theme_label"))
                    # 兜底：用每篇文章自己的 angle
                    for a in articles_for_prompt:
                        article_angles[a["article_id"]] = a.get("angle", "")
                    divergence_points = []

            # 回填 db
            theme_repo.update(
                theme["theme_id"],
                article_angles=article_angles,
                divergence_points=divergence_points,
            )

            updated.append({**theme, "article_angles": article_angles, "divergence_points": divergence_points})

        logger.info(
            "angle_compare: %d themes updated", len(updated),
        )
        return {"merged_themes": updated}

    return angle_compare_node

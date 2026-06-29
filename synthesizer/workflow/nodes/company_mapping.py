"""company_mapping_node: 公司/产业链映射。

对每个 merged_theme，把涉及文章的 companies / catalysts / industry_segments
喂给 LLM，整理产业链上中下游与公司映射，回填：
  - upstream / midstream / downstream: list[str]
  - companies: list[{name, direction, article_ids}]
  - catalysts: list[str]（去重汇总）
"""
from __future__ import annotations

import logging

from synthesizer.repositories import ThemeRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import build_company_prompt
from synthesizer.workflow.state import MergedThemeData, WorkflowState

logger = logging.getLogger(__name__)


def build_company_mapping_node(db, llm: LLMFusionClient | None = None):
    if llm is None:
        llm = LLMFusionClient()

    def company_mapping_node(state: WorkflowState) -> dict:
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
                        "companies": n.get("companies", []),
                        "catalysts": n.get("catalysts", []),
                        "industry_segments": n.get("industry_segments", []),
                    })

            upstream: list[str] = []
            midstream: list[str] = []
            downstream: list[str] = []
            companies: list[dict] = []
            catalysts: list[str] = []

            if articles_for_prompt:
                try:
                    data = llm.complete_json(
                        system="你是产业链映射专家。只输出 JSON。",
                        user=build_company_prompt(theme["theme_label"], articles_for_prompt),
                    )
                    upstream = data.get("upstream", []) or []
                    midstream = data.get("midstream", []) or []
                    downstream = data.get("downstream", []) or []
                    companies = data.get("companies", []) or []
                    catalysts = data.get("catalysts", []) or []
                except Exception as exc:
                    logger.exception("company_mapping LLM failed for theme %s", theme.get("theme_label"))
                    # 兜底：汇总各文 companies / catalysts / industry_segments
                    seen_c: set[str] = set()
                    seen_cat: set[str] = set()
                    seen_seg: set[str] = set()
                    for a in articles_for_prompt:
                        for c in a.get("companies", []):
                            if c and c not in seen_c:
                                seen_c.add(c)
                                companies.append({"name": c, "direction": "", "article_ids": [a["article_id"]]})
                        for cat in a.get("catalysts", []):
                            if cat and cat not in seen_cat:
                                seen_cat.add(cat)
                                catalysts.append(cat)
                        for seg in a.get("industry_segments", []):
                            if seg and seg not in seen_seg:
                                seen_seg.add(seg)
                                midstream.append(seg)

            theme_repo.update(
                theme["theme_id"],
                upstream=upstream,
                midstream=midstream,
                downstream=downstream,
                companies=companies,
                catalysts=catalysts,
            )

            updated.append({
                **theme,
                "upstream": upstream,
                "midstream": midstream,
                "downstream": downstream,
                "companies": companies,
                "catalysts": catalysts,
            })

        logger.info("company_mapping: %d themes updated", len(updated))
        return {"merged_themes": updated}

    return company_mapping_node

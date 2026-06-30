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

            upstream: list[str] = list(theme.get("upstream", []) or [])
            midstream: list[str] = list(theme.get("midstream", []) or [])
            downstream: list[str] = list(theme.get("downstream", []) or [])
            companies: list[dict] = list(theme.get("companies", []) or [])
            catalysts: list[str] = list(theme.get("catalysts", []) or [])

            if articles_for_prompt and not (companies or catalysts or midstream):
                seen_c: set[str] = set()
                seen_cat: set[str] = set()
                seen_seg: set[str] = set()
                for article in articles_for_prompt:
                    for company in article.get("companies", []):
                        name = company.get("name") if isinstance(company, dict) else str(company)
                        if name and name not in seen_c:
                            seen_c.add(name)
                            companies.append({
                                "name": name,
                                "direction": company.get("related_direction", "") if isinstance(company, dict) else "",
                                "reasons": [company.get("reason", "")] if isinstance(company, dict) and company.get("reason") else [],
                                "segments": [company.get("segment", "")] if isinstance(company, dict) and company.get("segment") else [],
                                "source_unit_ids": [],
                                "article_ids": [article["article_id"]],
                            })
                    for catalyst in article.get("catalysts", []):
                        if catalyst and catalyst not in seen_cat:
                            seen_cat.add(catalyst)
                            catalysts.append(catalyst)
                    for segment in article.get("industry_segments", []):
                        if segment and segment not in seen_seg:
                            seen_seg.add(segment)
                            midstream.append(segment)

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

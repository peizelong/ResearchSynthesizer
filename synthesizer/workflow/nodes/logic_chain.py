"""logic_chain_node: 逻辑链重建。

对每个 merged_theme，把涉及文章的 logic_chains 与 background 喂给 LLM，
重建综合逻辑链，回填：
  - consensus: 多文共识（一句话）
  - combined_logic_chain: 完整逻辑链（箭头串联）
"""
from __future__ import annotations

import logging

from synthesizer.repositories import ThemeRepository
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import build_logic_prompt
from synthesizer.workflow.state import MergedThemeData, WorkflowState

logger = logging.getLogger(__name__)


def build_logic_chain_node(db, llm: LLMFusionClient | None = None):
    if llm is None:
        llm = LLMFusionClient()

    def logic_chain_node(state: WorkflowState) -> dict:
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
                        "background": n.get("background", ""),
                        "logic_chains": n.get("logic_chains", []),
                    })

            consensus = theme.get("consensus", "") or ""
            combined_logic_chain = theme.get("combined_logic_chain", "") or ""

            if articles_for_prompt and not combined_logic_chain:
                all_chains = []
                for article in articles_for_prompt:
                    all_chains.extend(article.get("logic_chains", []))
                combined_logic_chain = " | ".join(str(chain) for chain in all_chains if chain)

            theme_repo.update(
                theme["theme_id"],
                consensus=consensus or None,
                combined_logic_chain=combined_logic_chain or None,
            )

            updated.append({**theme, "consensus": consensus, "combined_logic_chain": combined_logic_chain})

        logger.info("logic_chain: %d themes updated", len(updated))
        return {"merged_themes": updated}

    return logic_chain_node

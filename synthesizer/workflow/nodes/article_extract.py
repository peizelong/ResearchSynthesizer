"""article_extract_node: 单文叙事提取。

调用 NarrativeExtractor 从每篇文章提取 ExtractedNarrative，持久化为
ArticleNarrative，并把内存态 ArticleNarrativeData 放入 state.narratives。

幂等：对已有 ArticleNarrative 的文章跳过。
"""
from __future__ import annotations

import logging

from synthesizer.extractors import NarrativeExtractor, get_extractor
from synthesizer.repositories import ArticleRepository, BatchRepository, NarrativeRepository
from synthesizer.workflow.state import ArticleNarrativeData, WorkflowState

logger = logging.getLogger(__name__)

PROMPT_VERSION = "unit_v2"


def build_article_extract_node(db, extractor: NarrativeExtractor | None = None):
    """返回绑定 db 的 article_extract_node 闭包。

    extractor 可注入（测试用），默认 get_extractor()。
    """
    if extractor is None:
        extractor = get_extractor()

    def article_extract_node(state: WorkflowState) -> dict:
        batch_repo = BatchRepository(db)
        article_repo = ArticleRepository(db)
        narrative_repo = NarrativeRepository(db)

        batch_repo.update_status(state["batch_id"], "running", stage="extract_narratives")

        narratives: list[ArticleNarrativeData] = []
        errors: list[str] = []
        model_tag = f"{extractor.model_name}:{PROMPT_VERSION}"

        for article_id in state["article_ids"]:
            article = article_repo.get(article_id)
            if not article:
                errors.append(f"article_extract: article {article_id} not found")
                continue

            # 幂等：已有 narrative 的文章跳过
            existing = narrative_repo.list_by_article(article_id)
            if existing and all(n.extractor_model == model_tag for n in existing):
                for n in existing:
                    narratives.append(_to_data(n))
                continue
            if existing:
                narrative_repo.delete_by_article(article_id)

            try:
                extracted = extractor.extract(article.title, article.content, source=article.source)
                units = extracted.as_units()
                for unit in units:
                    n = narrative_repo.create(
                        article_id=article_id,
                        main_themes=unit.main_themes,
                        background=extracted.article_summary or extracted.background or None,
                        catalysts=unit.catalysts,
                        industry_segments=unit.industry_segments,
                        companies=unit.companies,
                        logic_chains=unit.logic_chain,
                        angle=unit.angle or None,
                        sentiment=extracted.sentiment or None,
                        # 旧字段复用为 unit importance，避免当前 MVP 增加迁移成本。
                        time_window=unit.importance or None,
                        extractor_model=model_tag,
                    )
                    narratives.append(_to_data(n))
                article_repo.update_extraction_status(article_id, "extracted")
                logger.info(
                    "article_extract: article %s -> %d narrative units (model=%s)",
                    article_id, len(units), model_tag,
                )
            except Exception as exc:
                logger.exception("article_extract failed for article %s", article_id)
                article_repo.update_extraction_status(article_id, "failed")
                errors.append(f"article_extract: article {article_id}: {exc}")

        return {"narratives": narratives, "errors": errors}

    return article_extract_node


def _to_data(n) -> ArticleNarrativeData:
    themes = n.main_themes or []
    direction = themes[0] if themes else ""
    sub_direction = themes[1] if len(themes) > 1 else ""
    importance = n.time_window if n.time_window in {"core", "secondary", "mention"} else "core"
    return ArticleNarrativeData(
        narrative_id=n.id,
        article_id=n.article_id,
        main_themes=n.main_themes or [],
        direction=direction,
        sub_direction=sub_direction,
        unit_type="other",
        background=n.background or "",
        catalysts=n.catalysts or [],
        industry_segments=n.industry_segments or [],
        companies=n.companies or [],
        logic_chains=n.logic_chains or [],
        logic_chain=n.logic_chains or [],
        angle=n.angle or "",
        source_quotes=[],
        importance=importance,
        sentiment=n.sentiment or "中性",
        time_window=n.time_window or "",
    )

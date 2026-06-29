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

        for article_id in state["article_ids"]:
            article = article_repo.get(article_id)
            if not article:
                errors.append(f"article_extract: article {article_id} not found")
                continue

            # 幂等：已有 narrative 的文章跳过
            existing = narrative_repo.list_by_article(article_id)
            if existing:
                for n in existing:
                    narratives.append(_to_data(n))
                continue

            try:
                extracted = extractor.extract(article.title, article.content)
                n = narrative_repo.create(
                    article_id=article_id,
                    main_themes=extracted.main_themes,
                    background=extracted.background or None,
                    catalysts=extracted.catalysts,
                    industry_segments=extracted.industry_segments,
                    companies=extracted.companies,
                    logic_chains=extracted.logic_chains,
                    angle=extracted.angle or None,
                    sentiment=extracted.sentiment or None,
                    time_window=extracted.time_window or None,
                    extractor_model=extractor.model_name,
                )
                narratives.append(_to_data(n))
                article_repo.update_extraction_status(article_id, "extracted")
                logger.info(
                    "article_extract: article %s -> %d themes (model=%s)",
                    article_id, len(extracted.main_themes), extractor.model_name,
                )
            except Exception as exc:
                logger.exception("article_extract failed for article %s", article_id)
                article_repo.update_extraction_status(article_id, "failed")
                errors.append(f"article_extract: article {article_id}: {exc}")

        return {"narratives": narratives, "errors": errors}

    return article_extract_node


def _to_data(n) -> ArticleNarrativeData:
    return ArticleNarrativeData(
        narrative_id=n.id,
        article_id=n.article_id,
        main_themes=n.main_themes or [],
        background=n.background or "",
        catalysts=n.catalysts or [],
        industry_segments=n.industry_segments or [],
        companies=n.companies or [],
        logic_chains=n.logic_chains or [],
        angle=n.angle or "",
        sentiment=n.sentiment or "中性",
        time_window=n.time_window or "",
    )

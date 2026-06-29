import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import ArticleRepository, BatchRepository
from synthesizer.schemas import BatchCreateRequest, BatchResponse
from synthesizer.extractors import get_extractor
from synthesizer.workflow import run_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/batches", response_model=BatchResponse)
def create_batch(request: BatchCreateRequest, db: Session = Depends(get_db)):
    """创建研究批次。

    优先使用显式 article_ids；未传时按 source/date 条件自动匹配文章。
    """
    article_repo = ArticleRepository(db)
    batch_repo = BatchRepository(db)

    if request.article_ids:
        existing = [article_repo.get(article_id) for article_id in request.article_ids]
        article_ids = [article.id for article in existing if article is not None]
        if len(article_ids) != len(request.article_ids):
            missing = sorted(set(request.article_ids) - set(article_ids))
            raise HTTPException(400, f"Some articles were not found: {', '.join(missing)}")
    else:
        # 按条件查找文章
        articles = article_repo.list(source=request.source_filter[0] if request.source_filter else None, limit=5000)
        article_ids = [a.id for a in articles]

        # 日期过滤
        if request.date_from or request.date_to:
            article_ids = [
                a.id for a in articles
                if (not request.date_from or (a.published_at and a.published_at >= request.date_from))
                and (not request.date_to or (a.published_at and a.published_at <= request.date_to))
            ]

    if not article_ids:
        raise HTTPException(400, "No articles match the filter criteria")

    batch = batch_repo.create(
        name=request.name,
        description=request.description,
        article_ids=article_ids,
        source_filter=request.source_filter,
        date_from=request.date_from,
        date_to=request.date_to,
        config=request.config,
        status="pending",
    )
    return batch


@router.get("/batches", response_model=list[BatchResponse])
def list_batches(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    repo = BatchRepository(db)
    return repo.list(limit=limit, offset=offset)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    repo = BatchRepository(db)
    batch = repo.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch


@router.post("/batches/{batch_id}/run")
def run_batch(batch_id: str, db: Session = Depends(get_db)):
    """运行批次：Narrative Synthesizer 7 节点 workflow。

    article_extract → theme_cluster → theme_merge →
    angle_compare → logic_chain → company_mapping → report
    """
    batch_repo = BatchRepository(db)

    batch = batch_repo.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    try:
        extractor = get_extractor()
        final_state = run_workflow(
            db=db,
            batch_id=batch_id,
            article_ids=batch.article_ids,
            extractor=extractor,
        )
        return {
            "status": "completed",
            "batch_id": batch_id,
            "narratives_count": len(final_state.get("narratives", [])),
            "merged_themes_count": len(final_state.get("merged_themes", [])),
            "report": final_state.get("report", ""),
            "errors": final_state.get("errors", []),
        }
    except Exception as exc:
        batch_repo.update_status(batch_id, "failed", error=str(exc))
        raise HTTPException(500, f"Batch run failed: {exc}") from exc

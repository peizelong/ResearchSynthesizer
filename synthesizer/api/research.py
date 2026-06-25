from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from synthesizer.database import get_db
from synthesizer.repositories import ArticleRepository, ClaimRepository, BatchRepository, ClusterRepository
from synthesizer.schemas import BatchCreateRequest, BatchResponse, BatchRunRequest
from synthesizer.extractors import get_extractor
from synthesizer.clustering import ClusteringService

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/batches", response_model=BatchResponse)
def create_batch(request: BatchCreateRequest, db: Session = Depends(get_db)):
    """创建研究批次（自动匹配符合条件的文章）"""
    article_repo = ArticleRepository(db)
    batch_repo = BatchRepository(db)

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
def run_batch(batch_id: str, request: BatchRunRequest, db: Session = Depends(get_db)):
    """运行批次：抽取 claims + 聚类"""
    batch_repo = BatchRepository(db)
    article_repo = ArticleRepository(db)
    claim_repo = ClaimRepository(db)

    batch = batch_repo.get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    try:
        # 阶段1: 抽取 claims
        if request.extract:
            batch_repo.update_status(batch_id, "running", stage="extract_claims")
            extractor = get_extractor()

            for article_id in batch.article_ids:
                article = article_repo.get(article_id)
                if not article or article.extraction_status == "extracted":
                    continue
                article_repo.update_extraction_status(article_id, "extracting")
                try:
                    extracted = extractor.extract(article.title, article.content)
                    for c in extracted:
                        claim_repo.create(
                            article_id=article_id,
                            claim_type=c.claim_type,
                            subject=c.subject,
                            predicate=c.predicate,
                            object_value=c.object_value,
                            direction_tag=c.direction_tag,
                            direction_angle=c.direction_angle,
                            evidence_text=c.evidence_text,
                            confidence=c.confidence,
                            extractor_model=extractor.model_name,
                        )
                    article_repo.update_extraction_status(article_id, "extracted")
                except Exception as exc:
                    article_repo.update_extraction_status(article_id, "failed")

        # 阶段2: 聚类
        if request.cluster:
            service = ClusteringService(db)
            clusters = service.cluster_batch(batch_id)

        return {"status": "completed", "batch_id": batch_id}
    except Exception as exc:
        batch_repo.update_status(batch_id, "failed", error=str(exc))
        raise HTTPException(500, f"Batch run failed: {exc}") from exc

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import ArticleRepository, ClaimRepository
from synthesizer.schemas import ArticleResponse, ArticleListItem, CrawlRequest
from synthesizer.crawlers import crawler_controller
from synthesizer.extractors import get_extractor

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=list[ArticleListItem])
def list_articles(
    source: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repo = ArticleRepository(db)
    return repo.list(source=source, limit=limit, offset=offset)


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: str, db: Session = Depends(get_db)):
    repo = ArticleRepository(db)
    article = repo.get(article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    return article


@router.post("/crawl")
def trigger_crawl(request: CrawlRequest):
    """触发爬虫"""
    try:
        return crawler_controller.start(request.model_dump())
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/crawl/status")
def crawl_status(source: str = Query("jiuyan_web")):
    """爬虫状态"""
    try:
        return crawler_controller.get_status(source)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{article_id}/extract")
def extract_claims(article_id: str, db: Session = Depends(get_db)):
    """对单篇文章抽取 claims"""
    article_repo = ArticleRepository(db)
    claim_repo = ClaimRepository(db)

    article = article_repo.get(article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    if article.extraction_status == "extracted":
        return {"status": "already_extracted", "claims_count": len(claim_repo.list_by_article(article_id))}

    try:
        article_repo.update_extraction_status(article_id, "extracting")
        extractor = get_extractor()
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
        return {"status": "extracted", "claims_count": len(extracted)}
    except Exception as exc:
        article_repo.update_extraction_status(article_id, "failed")
        raise HTTPException(500, f"Extraction failed: {exc}") from exc

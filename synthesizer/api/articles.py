from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import ArticleRepository, NarrativeRepository
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
def extract_narrative(article_id: str, db: Session = Depends(get_db)):
    """对单篇文章提取叙事（Narrative Synthesizer）。"""
    article_repo = ArticleRepository(db)
    narrative_repo = NarrativeRepository(db)

    article = article_repo.get(article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    existing = narrative_repo.list_by_article(article_id)
    if existing:
        return {"status": "already_extracted", "narratives_count": len(existing)}

    try:
        article_repo.update_extraction_status(article_id, "extracting")
        extractor = get_extractor()
        extracted = extractor.extract(article.title, article.content)
        narrative_repo.create(
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
        article_repo.update_extraction_status(article_id, "extracted")
        return {"status": "extracted", "themes_count": len(extracted.main_themes)}
    except Exception as exc:
        article_repo.update_extraction_status(article_id, "failed")
        raise HTTPException(500, f"Extraction failed: {exc}") from exc

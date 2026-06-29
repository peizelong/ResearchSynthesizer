from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import BatchRepository, NarrativeRepository, ThemeRepository
from synthesizer.schemas import NarrativeResponse, ThemeResponse

router = APIRouter(prefix="/api/themes", tags=["themes"])


@router.get("", response_model=list[ThemeResponse])
def list_themes(
    batch_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """列出融合主题。"""
    repo = ThemeRepository(db)
    return repo.list(batch_id=batch_id, limit=limit, offset=offset)


@router.get("/{theme_id}", response_model=ThemeResponse)
def get_theme(theme_id: str, db: Session = Depends(get_db)):
    repo = ThemeRepository(db)
    theme = repo.get(theme_id)
    if not theme:
        raise HTTPException(404, "Theme not found")
    return theme


@router.get("/batch/{batch_id}", response_model=list[ThemeResponse])
def list_themes_by_batch(batch_id: str, db: Session = Depends(get_db)):
    """列出某批次的全部融合主题。"""
    repo = ThemeRepository(db)
    return repo.list_by_batch(batch_id)


@router.get("/batch/{batch_id}/narratives", response_model=list[NarrativeResponse])
def list_narratives_by_batch(batch_id: str, db: Session = Depends(get_db)):
    """列出某批次的全部文章叙事。"""
    batch = BatchRepository(db).get(batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    repo = NarrativeRepository(db)
    return repo.list_by_article_ids(batch.article_ids or [])

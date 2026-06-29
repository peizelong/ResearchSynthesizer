from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import (
    ArticleRepository,
    BatchRepository,
    NarrativeRepository,
    ThemeRepository,
)

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return {
        "articles": ArticleRepository(db).count(),
        "narratives": NarrativeRepository(db).count(),
        "batches": BatchRepository(db).list(limit=100).__len__(),
        "merged_themes": ThemeRepository(db).count(),
    }

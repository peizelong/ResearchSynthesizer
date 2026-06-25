from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from synthesizer.database import get_db
from synthesizer.repositories import ClusterRepository, ClaimRepository
from synthesizer.schemas import ClusterResponse, ClusterDetailResponse, ClaimResponse

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterResponse])
def list_clusters(
    batch_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repo = ClusterRepository(db)
    return repo.list(batch_id=batch_id, limit=limit, offset=offset)


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
def get_cluster(cluster_id: str, db: Session = Depends(get_db)):
    repo = ClusterRepository(db)
    claim_repo = ClaimRepository(db)
    cluster = repo.get(cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster not found")
    claims = claim_repo.list_by_cluster(cluster_id)
    detail = ClusterDetailResponse.model_validate(cluster)
    detail.claims = [ClaimResponse.model_validate(c).model_dump() for c in claims]
    return detail


@router.get("/{cluster_id}/claims", response_model=list[ClaimResponse])
def get_cluster_claims(cluster_id: str, db: Session = Depends(get_db)):
    repo = ClaimRepository(db)
    cluster_exists = ClusterRepository(db).get(cluster_id)
    if not cluster_exists:
        raise HTTPException(404, "Cluster not found")
    return repo.list_by_cluster(cluster_id)

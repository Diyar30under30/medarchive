"""Full-text search across services + partners (brief §11).

Postgres path uses ILIKE + trigram (works with the pg_trgm index); SQLite dev
uses ILIKE. Fast on the demo dataset; both meet the ~1s latency target.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.models.service import Service
from app.normalization.preprocess import canonicalize
from app.schemas.schemas import PartnerOut, SearchResult, ServiceOut

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResult)
def search(
    q: str = Query(..., min_length=1, description="Query across services + partners"),
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100),
):
    like = f"%{q.strip()}%"
    # Also try the canonical form so abbreviations (ОАК) hit canonical names.
    canon = canonicalize(q)
    canon_like = f"%{canon}%" if canon else like

    svc_stmt = (
        select(Service)
        .where(
            Service.is_active.is_(True),
            or_(Service.service_name.ilike(like), Service.service_name.ilike(canon_like)),
        )
        .order_by(Service.service_name)
        .limit(limit)
    )
    services = db.scalars(svc_stmt).all()

    ptr_stmt = (
        select(Partner)
        .where(or_(Partner.name.ilike(like), Partner.city.ilike(like)))
        .order_by(Partner.name)
        .limit(limit)
    )
    partners = db.scalars(ptr_stmt).all()

    return SearchResult(
        services=[ServiceOut.model_validate(s) for s in services],
        partners=[PartnerOut.model_validate(p) for p in partners],
    )

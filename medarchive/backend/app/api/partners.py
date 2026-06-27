"""Partner endpoints (brief §11)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.models.price_item import PriceItem
from app.models.service import Service
from app.schemas.schemas import PartnerOut, PriceItemOut

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("", response_model=list[PartnerOut])
def list_partners(
    db: Session = Depends(get_db),
    city: str | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None, description="Search by name"),
):
    stmt = select(Partner)
    if city:
        stmt = stmt.where(Partner.city == city)
    if is_active is not None:
        stmt = stmt.where(Partner.is_active.is_(is_active))
    if q:
        stmt = stmt.where(Partner.name.ilike(f"%{q}%"))
    rows = db.scalars(stmt.order_by(Partner.name)).all()
    return [PartnerOut.model_validate(r) for r in rows]


@router.get("/{partner_id}/services", response_model=list[PriceItemOut])
def partner_services(partner_id: str, db: Session = Depends(get_db)):
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(404, "partner not found")
    stmt = (
        select(PriceItem, Service.service_name)
        .outerjoin(Service, PriceItem.service_id == Service.service_id)
        .where(PriceItem.partner_id == partner_id, PriceItem.is_active.is_(True))
        .order_by(PriceItem.service_name_raw)
    )
    out: list[PriceItemOut] = []
    for it, svc_name in db.execute(stmt).all():
        m = PriceItemOut.model_validate(it)
        m.service_name = svc_name
        m.match_method = it.match_method.value
        m.currency_original = it.currency_original.value
        out.append(m)
    return out

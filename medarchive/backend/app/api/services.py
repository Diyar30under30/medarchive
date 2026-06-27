"""Services + directory endpoints (brief §11)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.models.price_item import PriceItem
from app.models.service import Service
from app.schemas.schemas import (
    PartnerPriceOut,
    PriceHistoryEntry,
    PriceHistoryOut,
    ServiceListOut,
    ServiceOut,
)

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=ServiceListOut)
def list_services(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="Filter by Специальность"),
    q: str | None = Query(None, description="Search by name (substring)"),
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    stmt = select(Service).where(Service.is_active.is_(True))
    if category:
        stmt = stmt.where(Service.category == category)
    if q:
        stmt = stmt.where(Service.service_name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Service.service_name).limit(limit).offset(offset)).all()
    return ServiceListOut(total=total, items=[ServiceOut.model_validate(r) for r in rows])


@router.get("/{service_id}/partners", response_model=list[PartnerPriceOut])
def service_partners(
    service_id: str,
    db: Session = Depends(get_db),
    sort: str = Query("price", pattern="^(price|date)$"),
):
    svc = db.get(Service, service_id)
    if svc is None:
        raise HTTPException(404, "service not found")
    stmt = (
        select(PriceItem, Partner)
        .join(Partner, PriceItem.partner_id == Partner.partner_id)
        .where(PriceItem.service_id == service_id, PriceItem.is_active.is_(True))
    )
    out = [
        PartnerPriceOut(
            partner_id=p.partner_id,
            partner_name=p.name,
            city=p.city,
            address=p.address,
            price_resident_kzt=it.price_resident_kzt,
            price_nonresident_kzt=it.price_nonresident_kzt,
            currency_original=it.currency_original.value,
            price_original=it.price_original,
            effective_date=it.effective_date,
            is_verified=it.is_verified,
        )
        for it, p in db.execute(stmt).all()
    ]
    if sort == "price":
        out.sort(key=lambda x: (x.price_resident_kzt is None, x.price_resident_kzt or 0))
    else:
        out.sort(key=lambda x: (x.effective_date is None, x.effective_date or ""), reverse=True)
    return out


@router.get("/{service_id}/price-history", response_model=PriceHistoryOut)
def price_history(service_id: str, db: Session = Depends(get_db)):
    svc = db.get(Service, service_id)
    if svc is None:
        raise HTTPException(404, "service not found")
    stmt = (
        select(PriceItem, Partner)
        .join(Partner, PriceItem.partner_id == Partner.partner_id)
        .where(PriceItem.service_id == service_id)
        .order_by(PriceItem.effective_date.desc().nullslast())
    )
    entries = [
        PriceHistoryEntry(
            item_id=it.item_id,
            partner_id=it.partner_id,
            partner_name=p.name,
            price_resident_kzt=it.price_resident_kzt,
            price_nonresident_kzt=it.price_nonresident_kzt,
            effective_date=it.effective_date,
            is_active=it.is_active,
            superseded_by=it.superseded_by,
        )
        for it, p in db.execute(stmt).all()
    ]
    return PriceHistoryOut(service_id=service_id, service_name=svc.service_name, entries=entries)

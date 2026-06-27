"""Part B: anomaly listing + export (brief §B4, §B6)."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.models.price_item import PriceItem
from app.models.service import Service

router = APIRouter(tags=["analytics"])

# Anomaly codes the validation engine writes into verification_note.
_ANOMALY_CODES = ["price_jump", "nonresident_lt_resident", "future_date", "nonpositive_price"]


def _active_rows(db: Session):
    stmt = (
        select(PriceItem, Partner, Service)
        .join(Partner, PriceItem.partner_id == Partner.partner_id)
        .outerjoin(Service, PriceItem.service_id == Service.service_id)
        .where(PriceItem.is_active.is_(True))
        .order_by(Partner.name)
    )
    return db.execute(stmt).all()


@router.get("/anomalies")
def anomalies(db: Session = Depends(get_db), limit: int = Query(200, le=1000)) -> list[dict]:
    conds = [PriceItem.verification_note.ilike(f"%{c}%") for c in _ANOMALY_CODES]
    stmt = (
        select(PriceItem, Partner, Service)
        .join(Partner, PriceItem.partner_id == Partner.partner_id)
        .outerjoin(Service, PriceItem.service_id == Service.service_id)
        .where(PriceItem.verification_note.isnot(None), or_(*conds))
        .limit(limit)
    )
    out = []
    for it, p, svc in db.execute(stmt).all():
        note = it.verification_note or ""
        kind = next((c for c in _ANOMALY_CODES if c in note), "other")
        out.append({
            "item_id": it.item_id,
            "kind": kind,
            "note": note,
            "service_name_raw": it.service_name_raw,
            "service_name": svc.service_name if svc else None,
            "service_id": it.service_id,
            "partner_name": p.name,
            "city": p.city,
            "price_resident_kzt": float(it.price_resident_kzt) if it.price_resident_kzt is not None else None,
            "price_nonresident_kzt": float(it.price_nonresident_kzt) if it.price_nonresident_kzt is not None else None,
            "effective_date": it.effective_date.isoformat() if it.effective_date else None,
        })
    return out


_EXPORT_HEADERS = [
    "partner", "city", "bin", "service_canonical", "service_raw", "category",
    "price_resident_kzt", "price_nonresident_kzt", "currency_original",
    "price_original", "effective_date", "match_method", "match_confidence", "verified",
]


def _export_records(db: Session):
    for it, p, svc in _active_rows(db):
        yield {
            "partner": p.name, "city": p.city or "", "bin": p.bin or "",
            "service_canonical": svc.service_name if svc else "",
            "service_raw": it.service_name_raw,
            "category": svc.category if svc else "",
            "price_resident_kzt": it.price_resident_kzt,
            "price_nonresident_kzt": it.price_nonresident_kzt,
            "currency_original": it.currency_original.value,
            "price_original": it.price_original,
            "effective_date": it.effective_date.isoformat() if it.effective_date else "",
            "match_method": it.match_method.value,
            "match_confidence": it.match_confidence,
            "verified": it.is_verified,
        }


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db)):
    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel reads UTF-8 Cyrillic correctly
    w = csv.DictWriter(buf, fieldnames=_EXPORT_HEADERS)
    w.writeheader()
    for rec in _export_records(db):
        w.writerow({k: ("" if v is None else v) for k, v in rec.items()})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=medarchive_export.csv"},
    )


@router.get("/export.xlsx")
def export_xlsx(db: Session = Depends(get_db)):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Прайс"
    ws.append(_EXPORT_HEADERS)
    for rec in _export_records(db):
        ws.append([rec[h] for h in _EXPORT_HEADERS])
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return Response(
        out.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=medarchive_export.xlsx"},
    )

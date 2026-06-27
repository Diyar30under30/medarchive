"""Operator console endpoints: review queue + manual match (brief §11).

GET /unmatched — the verification queue (low-confidence / unmatched / anomalies).
POST /match — confirm/correct/reject a row; confirming triggers synonym learning.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import MatchMethod, ReviewStatus
from app.models.partner import Partner
from app.models.price_item import PriceItem
from app.models.review import MatchReviewItem
from app.models.service import Service
from app.normalization.learning import learn_synonym
from app.normalization.reference_loader import _NS
from app.schemas.schemas import MatchRequest, MatchResponse, ReviewItemOut
from app.versioning.history import apply_versioning

router = APIRouter(tags=["operator"])


@router.get("/unmatched", response_model=list[ReviewItemOut])
def unmatched(
    db: Session = Depends(get_db),
    status: str = Query("open", pattern="^(open|confirmed|corrected|rejected|all)$"),
    limit: int = Query(100, le=500),
):
    stmt = (
        select(MatchReviewItem, PriceItem, Partner)
        .join(PriceItem, MatchReviewItem.item_id == PriceItem.item_id)
        .join(Partner, PriceItem.partner_id == Partner.partner_id)
    )
    if status != "all":
        stmt = stmt.where(MatchReviewItem.status == ReviewStatus(status))
    stmt = stmt.limit(limit)

    out: list[ReviewItemOut] = []
    for rev, it, p in db.execute(stmt).all():
        out.append(
            ReviewItemOut(
                review_id=rev.review_id,
                item_id=it.item_id,
                service_name_raw=it.service_name_raw,
                source_fragment=it.verification_note or it.service_name_raw,
                partner_name=p.name,
                price_resident_kzt=it.price_resident_kzt,
                price_nonresident_kzt=it.price_nonresident_kzt,
                candidates=rev.candidates or [],
                specialty_hint=rev.specialty_hint,
                status=rev.status.value,
            )
        )
    return out


@router.post("/match", response_model=MatchResponse)
def manual_match(req: MatchRequest, db: Session = Depends(get_db)):
    item = db.get(PriceItem, req.item_id)
    if item is None:
        raise HTTPException(404, "price item not found")
    review = db.scalar(select(MatchReviewItem).where(MatchReviewItem.item_id == req.item_id))

    # Reject — leave unmatched.
    if req.reject:
        item.service_id = None
        item.match_method = MatchMethod.none
        item.is_verified = False
        item.verification_note = req.note or "rejected by operator"
        if review:
            review.status = ReviewStatus.rejected
        db.commit()
        return MatchResponse(item_id=item.item_id, service_id=None,
                             match_method="none", is_verified=False,
                             message="row rejected")

    # Create a new directory entry.
    if req.new_service_name:
        category = req.new_service_category or "Прочее"
        sid = str(uuid.uuid5(_NS, f"{category}|manual|{req.new_service_name}"))
        service = db.get(Service, sid) or Service(
            service_id=sid, service_name=req.new_service_name.strip(),
            category=category, synonyms=[], is_active=True,
        )
        db.add(service)
        db.flush()
    elif req.service_id:
        service = db.get(Service, req.service_id)
        if service is None:
            raise HTTPException(404, "target service not found")
    else:
        raise HTTPException(422, "provide service_id, new_service_name, or reject=true")

    # Confirm the mapping + learn the synonym.
    learned = learn_synonym(db, service, item.service_name_raw)
    item.service_id = service.service_id
    item.match_method = MatchMethod.manual
    item.match_confidence = 1.0
    item.is_verified = True
    if req.note:
        item.verification_note = req.note
    db.flush()
    apply_versioning(db, item)

    if review:
        review.status = ReviewStatus.corrected if req.new_service_name else ReviewStatus.confirmed
    db.commit()

    return MatchResponse(
        item_id=item.item_id,
        service_id=service.service_id,
        match_method="manual",
        is_verified=True,
        learned_synonym=learned,
        message=f"mapped to '{service.service_name}'"
        + (f"; learned synonym '{learned}'" if learned else ""),
    )

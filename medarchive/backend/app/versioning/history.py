"""Price versioning & history (brief §10).

Prices are versioned, never overwritten. When a newer-dated document changes a
partner's price for a service, the prior active PriceItem is marked inactive and
linked via superseded_by. Same (partner, service, date) duplicates dedup to the
newest row. History is retained indefinitely.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price_item import PriceItem

log = logging.getLogger("medarchive.versioning")


def latest_active(db: Session, partner_id: str, service_id: str) -> PriceItem | None:
    """Most recent active priced row for a partner+service (for anomaly compare)."""
    stmt = (
        select(PriceItem)
        .where(
            PriceItem.partner_id == partner_id,
            PriceItem.service_id == service_id,
            PriceItem.is_active.is_(True),
        )
        .order_by(PriceItem.effective_date.desc().nullslast())
    )
    return db.scalars(stmt).first()


def apply_versioning(db: Session, new_item: PriceItem) -> None:
    """Supersede prior active rows for the same partner+service.

    - If a prior active row is OLDER-or-equal dated → mark it superseded by new.
    - If a prior active row is NEWER dated → the incoming row is historical;
      mark the NEW row inactive and point it at the newer one.
    Same-date rows are treated as duplicates: newest insert wins, prior archived.
    Requires new_item.service_id to be set (unmatched rows are not versioned).
    """
    if not new_item.service_id:
        return

    stmt = select(PriceItem).where(
        PriceItem.partner_id == new_item.partner_id,
        PriceItem.service_id == new_item.service_id,
        PriceItem.is_active.is_(True),
        PriceItem.item_id != new_item.item_id,
    )
    priors = db.scalars(stmt).all()

    new_date = new_item.effective_date
    for prior in priors:
        prior_date = prior.effective_date
        # Compare; None dates sort oldest.
        if prior_date is not None and new_date is not None and prior_date > new_date:
            # Incoming is older history → keep prior active, archive the new row.
            new_item.is_active = False
            new_item.superseded_by = prior.item_id
        else:
            # Incoming is newer or same date → it supersedes the prior.
            prior.is_active = False
            prior.superseded_by = new_item.item_id
    db.flush()
    log.debug(
        "Versioning: item=%s superseded %d prior row(s)",
        new_item.item_id, sum(1 for p in priors if not p.is_active)
    )

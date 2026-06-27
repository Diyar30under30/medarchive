"""Synonym-learning loop (brief §8.8).

When an operator confirms raw → service, the canonical form of the raw name is
appended to that Service.synonyms so identical/similar future rows auto-match via
the exact/synonym short-circuit. This is what lifts the auto-match rate over a run.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.service import Service
from app.normalization.preprocess import canonicalize

log = logging.getLogger("medarchive.learning")


def learn_synonym(db: Session, service: Service, raw_name: str) -> str | None:
    """Append the canonical raw form to the service's synonyms (idempotent)."""
    canon = canonicalize(raw_name)
    if not canon:
        return None
    # Don't store a synonym identical to the canonical service name.
    if canon == canonicalize(service.service_name):
        return None
    existing = set(service.synonyms or [])
    if canon in existing:
        return None
    service.synonyms = sorted(existing | {canon})
    db.add(service)
    log.info("Learned synonym %r → %s", canon, service.service_name)
    return canon

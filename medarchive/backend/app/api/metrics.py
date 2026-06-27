"""Quality report endpoint (brief §11, §15) — the headline demo metric."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.reporting.quality import compute_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    """Documents processed, % auto-normalized, review/unmatched counts, anomalies,
    per-format success rates, matches-by-method."""
    return compute_metrics(db)

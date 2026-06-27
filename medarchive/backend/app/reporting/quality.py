"""Quality report (brief §15) — the headline demo metric.

compute_metrics(db) returns the live, DB-wide numbers used by GET /metrics and the
dashboard. write_quality_report also persists a JSON snapshot after each ingest.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import PriceDocument
from app.models.enums import MatchMethod, ParseStatus, ReviewStatus
from app.models.price_item import PriceItem
from app.models.review import MatchReviewItem
from app.models.service import Service


def compute_metrics(db: Session) -> dict:
    total_docs = db.scalar(select(func.count()).select_from(PriceDocument)) or 0
    docs_by_status = {
        s.value: db.scalar(
            select(func.count()).select_from(PriceDocument).where(PriceDocument.parse_status == s)
        ) or 0
        for s in ParseStatus
    }

    total_positions = db.scalar(select(func.count()).select_from(PriceItem)) or 0
    verified = db.scalar(
        select(func.count()).select_from(PriceItem).where(PriceItem.is_verified.is_(True))
    ) or 0
    matched = db.scalar(
        select(func.count()).select_from(PriceItem).where(PriceItem.service_id.isnot(None))
    ) or 0
    unmatched = total_positions - matched

    by_method = {
        m.value: db.scalar(
            select(func.count()).select_from(PriceItem).where(PriceItem.match_method == m)
        ) or 0
        for m in MatchMethod
    }

    review_open = db.scalar(
        select(func.count()).select_from(MatchReviewItem).where(
            MatchReviewItem.status == ReviewStatus.open
        )
    ) or 0
    anomalies = db.scalar(
        select(func.count()).select_from(PriceItem).where(
            PriceItem.verification_note.ilike("%price_jump%")
        )
    ) or 0

    services = db.scalar(select(func.count()).select_from(Service)) or 0
    # Synonyms learned from operator confirmations (the learning loop, brief §8.8).
    synonyms_learned = sum(
        len(s or []) for s in db.scalars(select(Service.synonyms)).all()
    )

    # Per-format success rate.
    per_format: dict = {}
    fmt_rows = db.execute(
        select(PriceDocument.file_format, PriceDocument.parse_status)
    ).all()
    for fmt, status in fmt_rows:
        key = fmt.value if hasattr(fmt, "value") else str(fmt)
        d = per_format.setdefault(key, {"total": 0, "ok": 0})
        d["total"] += 1
        if status in (ParseStatus.done, ParseStatus.needs_review):
            d["ok"] += 1
    for d in per_format.values():
        d["success_rate"] = (d["ok"] / d["total"]) if d["total"] else 0.0

    auto_rate = (verified / total_positions) if total_positions else 0.0

    return {
        "services_in_directory": services,
        "synonyms_learned": synonyms_learned,
        "documents_total": total_docs,
        "documents_by_status": docs_by_status,
        "documents_errored": docs_by_status.get("error", 0),
        "positions_total": total_positions,
        "auto_matched": verified,
        "matched_any": matched,
        "unmatched": unmatched,
        "review_queue_open": review_open,
        "auto_normalization_rate": round(auto_rate, 4),
        "anomalies_flagged": anomalies,
        "matches_by_method": by_method,
        "per_format_success": per_format,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_quality_report(db: Session, counters, archive_name: str) -> dict:
    metrics = compute_metrics(db)
    report = {
        "archive": archive_name,
        "last_run": counters.as_dict() if hasattr(counters, "as_dict") else {},
        "global": metrics,
    }
    out_dir = settings.incoming_path
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir.parent / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report

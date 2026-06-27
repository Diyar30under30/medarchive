"""End-to-end ingestion pipeline (brief §7).

unzip → per file: detect → extract (raw preserved) → normalize/match → validate
→ currency convert → version → persist PriceItems → set document status. One bad
file never halts the batch. Returns counters for the Job + quality report.
"""
from __future__ import annotations

import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.extractors import get_extractor
from app.extractors.base import ExtractedRow, ExtractionResult
from app.ingestion.detect import detect_format
from app.ingestion.partner import parse_effective_date, parse_partner_meta, resolve_partner
from app.models.document import PriceDocument
from app.models.enums import Currency, MatchMethod, ParseStatus
from app.models.price_item import PriceItem
from app.models.review import MatchReviewItem
from app.models.service import Service
from app.normalization.matcher import AUTO, REVIEW, Matcher, ServiceIndex
from app.validation.currency import to_kzt
from app.validation.rules import RowToValidate, validate_row
from app.versioning.history import apply_versioning, latest_active

log = logging.getLogger("medarchive.pipeline")


@dataclass
class IngestCounters:
    total_files: int = 0
    processed_files: int = 0
    errored_files: int = 0
    total_positions: int = 0
    auto_matched: int = 0
    review: int = 0
    unmatched: int = 0
    anomalies: int = 0
    skipped_rows: int = 0
    per_format: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["auto_match_rate"] = (
            self.auto_matched / self.total_positions if self.total_positions else 0.0
        )
        return d


def build_matcher(db: Session) -> Matcher:
    rows = [
        {
            "service_id": s.service_id,
            "service_name": s.service_name,
            "category": s.category,
            "synonyms": s.synonyms or [],
            "embedding": s.embedding,
        }
        for s in db.scalars(select(Service)).all()
    ]
    return Matcher(ServiceIndex.from_rows(rows))


def process_archive(db: Session, zip_path: Path, counters: IngestCounters | None = None,
                    on_progress=None) -> IngestCounters:
    counters = counters or IngestCounters()
    matcher = build_matcher(db)
    raw_store = settings.raw_store_path
    raw_store.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        counters.total_files = len(names)
        extract_dir = raw_store / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)

        for name in names:
            safe_name = Path(name).name
            target = extract_dir / safe_name
            try:
                with zf.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                process_document(db, target, safe_name, matcher, counters)
            except Exception as exc:  # noqa: BLE001 — fault tolerance
                log.exception("File %s failed", safe_name)
                counters.errored_files += 1
                _record_failed_doc(db, safe_name, str(target), str(exc))
            finally:
                counters.processed_files += 1
                if on_progress:
                    on_progress(counters)
        db.commit()
    return counters


def _record_failed_doc(db: Session, file_name: str, stored_path: str, err: str) -> None:
    from app.models.enums import FileFormat

    fmt = FileFormat.pdf
    try:
        fmt = detect_format(Path(stored_path))
    except Exception:  # noqa: BLE001
        pass
    doc = PriceDocument(
        file_name=file_name, file_format=fmt, parse_status=ParseStatus.error,
        parse_log=f"unhandled error: {err}", stored_path=stored_path,
        parsed_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.flush()


def process_document(db: Session, path: Path, file_name: str, matcher: Matcher,
                     counters: IngestCounters) -> PriceDocument:
    fmt = detect_format(path)
    counters.per_format.setdefault(fmt.value, {"docs": 0, "ok": 0, "rows": 0})
    counters.per_format[fmt.value]["docs"] += 1

    try:
        result: ExtractionResult = get_extractor(fmt).extract(path)
    except Exception as exc:  # noqa: BLE001
        result = ExtractionResult(rows=[], raw_text="", log=f"extractor error: {exc}")

    meta = parse_partner_meta(result.raw_text, file_name)
    eff_date = parse_effective_date(result.raw_text, file_name)
    partner = resolve_partner(db, meta)

    doc = PriceDocument(
        partner_id=partner.partner_id,
        file_name=file_name,
        file_format=fmt,
        effective_date=eff_date,
        parsed_at=datetime.now(timezone.utc),
        parse_status=ParseStatus.processing,
        parse_log=result.log,
        raw_content=result.raw_text,
        stored_path=str(path),
    )
    db.add(doc)
    db.flush()

    if not result.rows:
        doc.parse_status = ParseStatus.error
        doc.parse_log = (result.log + " | no recognizable data").strip(" |")
        return doc

    needs_review_doc = False
    for row in result.rows:
        outcome = _process_row(db, doc, partner.partner_id, row, eff_date, matcher, counters)
        if outcome == "review":
            needs_review_doc = True

    counters.per_format[fmt.value]["ok"] += 1
    counters.per_format[fmt.value]["rows"] += len(result.rows)
    doc.parse_status = ParseStatus.needs_review if needs_review_doc else ParseStatus.done
    return doc


def _process_row(db: Session, doc: PriceDocument, partner_id: str, row: ExtractedRow,
                 eff_date, matcher: Matcher, counters: IngestCounters) -> str:
    # 1. match
    candidates = matcher.match(row.service_name_raw, specialty_hint=row.specialty_hint)
    top = candidates[0] if candidates else None
    bucket = matcher.classify(top.score) if top else "unmatched"

    service_id = top.service_id if top and bucket != "unmatched" else None
    confidence = top.score if top else None
    method = MatchMethod(top.method) if (top and bucket == AUTO) else (
        MatchMethod.none if bucket == "unmatched" else MatchMethod(top.method) if top else MatchMethod.none
    )

    # 2. currency convert (keep original)
    currency = (row.currency or "KZT").upper()
    try:
        currency_enum = Currency(currency)
    except ValueError:
        currency_enum = Currency.KZT
    res_kzt = to_kzt(row.price_resident, currency, eff_date)
    nonres_kzt = to_kzt(row.price_nonresident, currency, eff_date)
    price_original = _to_decimal(row.price_resident)

    # 3. prior version (for anomaly + supersession)
    prev = latest_active(db, partner_id, service_id) if service_id else None
    prev_price = prev.price_resident_kzt if prev else None

    # 4. validate
    vres = validate_row(
        RowToValidate(
            service_name_raw=row.service_name_raw,
            price_resident_kzt=res_kzt,
            price_nonresident_kzt=nonres_kzt,
            effective_date=eff_date,
            currency_original=currency,
            previous_resident_kzt=Decimal(str(prev_price)) if prev_price is not None else None,
        )
    )
    if vres.should_skip:
        counters.skipped_rows += 1
        return "skip"

    # Normalization (name→service) is auto-confirmed purely on match confidence
    # (brief §8.7). A price anomaly still queues the row for review, but does NOT
    # un-normalize it — the "% auto-normalized" metric measures name matching.
    is_match_auto = bucket == AUTO
    if vres.has_anomaly:
        counters.anomalies += 1

    item = PriceItem(
        doc_id=doc.doc_id,
        partner_id=partner_id,
        service_name_raw=row.service_name_raw,
        service_code_source=row.service_code_source,
        service_id=service_id,
        match_confidence=confidence,
        match_method=method,
        price_resident_kzt=res_kzt,
        price_nonresident_kzt=nonres_kzt,
        price_original=price_original,
        currency_original=currency_enum,
        is_verified=is_match_auto,
        verification_note=vres.note or None,
        effective_date=eff_date,
        is_active=True,
    )
    db.add(item)
    db.flush()

    if service_id:
        apply_versioning(db, item)

    counters.total_positions += 1
    if is_match_auto:
        counters.auto_matched += 1

    # Queue for the operator when the match is uncertain OR a price needs review.
    needs_queue = (bucket != AUTO) or vres.needs_review
    if needs_queue:
        cand_json = [c.as_dict() for c in candidates] if candidates else []
        db.add(MatchReviewItem(
            item_id=item.item_id, candidates=cand_json,
            specialty_hint=row.specialty_hint,
        ))
        if bucket != AUTO:
            if bucket == REVIEW:
                counters.review += 1
            else:
                counters.unmatched += 1

    return "auto" if (is_match_auto and not vres.needs_review) else "review"


def _to_decimal(v) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace(" ", "").replace(",", "."))
    except Exception:  # noqa: BLE001
        return None

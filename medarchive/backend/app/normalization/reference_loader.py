"""Load the canonical directory into the `services` table (brief §4).

Accepts XLSX or JSON with the same column mapping. Assigns a deterministic
internal service_id (UUID5 of Специальность|Code|Name_ru) because no source
column is a usable key. Idempotent: re-running upserts, never duplicates.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.service import Service
from app.normalization.embeddings import get_embedding_provider

log = logging.getLogger("medarchive.reference")

# Stable namespace so UUID5s are reproducible across runs/machines.
_NS = uuid.UUID("d3f1c0de-0000-4000-8000-000000000001")

# Source column → our field. Tolerant of minor header variations.
_COLMAP = {
    "ID": "group_id",
    "Специальность": "category",
    "Code": "source_code",
    "Name_ru": "service_name",
    "TarificatrCode": "tariff_code",
}


def service_uuid(category: str, source_code: str, name_ru: str) -> str:
    key = f"{category}|{source_code}|{name_ru}".strip()
    return str(uuid.uuid5(_NS, key))


def _read_xlsx(path: Path) -> list[dict]:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
    out: list[dict] = []
    for raw in rows_iter:
        if raw is None or all(c is None for c in raw):
            continue
        out.append({headers[i]: raw[i] for i in range(min(len(headers), len(raw)))})
    return out


def _read_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):  # allow {"services": [...]}
        data = data.get("services") or data.get("rows") or []
    return list(data)


def _normalize_row(raw: dict) -> dict | None:
    mapped = {dst: raw.get(src) for src, dst in _COLMAP.items()}
    name = (mapped.get("service_name") or "").strip() if mapped.get("service_name") else ""
    category = (mapped.get("category") or "").strip() if mapped.get("category") else ""
    if not name or not category:
        return None
    code = (str(mapped.get("source_code")).strip() if mapped.get("source_code") else "")
    tariff = mapped.get("tariff_code")
    tariff = str(tariff).strip() if tariff not in (None, "") else None
    return {
        "service_id": service_uuid(category, code, name),
        "service_name": name,
        "category": category,
        "source_code": code or None,
        "tariff_code": tariff,
    }


def find_reference_file() -> Path | None:
    ref_dir = settings.reference_path
    if not ref_dir.exists():
        return None
    # Prefer an explicit JSON, then any XLSX (real file name may vary).
    for pattern in ("*.json", "Справочник услуг.xlsx", "*.xlsx"):
        hits = sorted(ref_dir.glob(pattern))
        if hits:
            return hits[0]
    return None


def load_reference(db: Session, path: Path | None = None) -> dict:
    path = path or find_reference_file()
    if path is None or not path.exists():
        log.warning("No reference file found in %s", settings.reference_path)
        return {"loaded": 0, "updated": 0, "skipped": 0, "path": None}

    rows = _read_json(path) if path.suffix.lower() == ".json" else _read_xlsx(path)
    provider = get_embedding_provider()

    # Pre-embed all names in one batch when embeddings are available.
    normalized = [n for n in (_normalize_row(r) for r in rows) if n]
    embeddings: list[list[float]] | None = None
    if provider.available and normalized:
        embeddings = provider.encode_batch([n["service_name"] for n in normalized])

    created = updated = 0
    existing = {
        s.service_id: s
        for s in db.scalars(select(Service)).all()
    }
    for i, n in enumerate(normalized):
        emb = embeddings[i] if embeddings else None
        svc = existing.get(n["service_id"])
        if svc is None:
            svc = Service(
                service_id=n["service_id"],
                service_name=n["service_name"],
                category=n["category"],
                source_code=n["source_code"],
                tariff_code=n["tariff_code"],
                synonyms=[],
                embedding=emb,
                is_active=True,
            )
            db.add(svc)
            created += 1
        else:
            svc.service_name = n["service_name"]
            svc.category = n["category"]
            svc.source_code = n["source_code"]
            svc.tariff_code = n["tariff_code"]
            if emb is not None:
                svc.embedding = emb
            updated += 1
    db.commit()

    skipped = len(rows) - len(normalized)
    result = {
        "loaded": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(normalized),
        "embeddings": bool(embeddings),
        "path": str(path),
    }
    log.info("Reference load: %s", result)
    return result

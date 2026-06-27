"""Partner resolution (brief §6): parse clinic metadata from a document's raw
text / filename, then dedup by BIN when present, else by normalized name+city.
"""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.partner import Partner

_BIN_RE = re.compile(r"\b(\d{12})\b")
_DATE_RE = re.compile(r"(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})")
_LABELS = {
    "name": re.compile(r"(?:клиника|медцентр|организация|партнёр|партнер)\s*[:\-]\s*(.+)", re.I),
    "city": re.compile(r"(?:город|қала)\s*[:\-]\s*(.+)", re.I),
    "address": re.compile(r"(?:адрес|мекенжай)\s*[:\-]\s*(.+)", re.I),
    "phone": re.compile(r"(?:тел(?:ефон)?|phone)\s*[:\-]\s*(.+)", re.I),
}


def parse_partner_meta(raw_text: str, filename: str) -> dict:
    text = raw_text or ""
    meta: dict = {"name": None, "city": None, "address": None, "phone": None, "bin": None}

    for key, rx in _LABELS.items():
        m = rx.search(text)
        if m:
            meta[key] = m.group(1).strip().splitlines()[0][:200]

    bin_m = _BIN_RE.search(text)
    if bin_m:
        meta["bin"] = bin_m.group(1)

    # Fallback name from filename (text before the date token).
    if not meta["name"]:
        stem = filename.rsplit(".", 1)[0]
        stem = _DATE_RE.split(stem)[0]
        stem = re.sub(r"[_\-]+", " ", stem).strip(" _-")
        meta["name"] = stem.title() if stem else filename

    return meta


def parse_effective_date(raw_text: str, filename: str) -> date | None:
    for source in (filename, raw_text or ""):
        m = _DATE_RE.search(source)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            try:
                return date(y, mo, d)
            except ValueError:
                continue
    return None


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def resolve_partner(db: Session, meta: dict) -> Partner:
    """Find-or-create a partner, deduping by BIN, else normalized name+city."""
    bin_ = meta.get("bin")
    if bin_:
        existing = db.scalar(select(Partner).where(Partner.bin == bin_))
        if existing:
            return existing

    name, city = meta.get("name"), meta.get("city")
    if not bin_ and name:
        for p in db.scalars(select(Partner).where(Partner.bin.is_(None))).all():
            if _norm(p.name) == _norm(name) and _norm(p.city) == _norm(city):
                return p

    partner = Partner(
        name=name or "Неизвестный партнёр",
        city=city,
        address=meta.get("address"),
        contact_phone=meta.get("phone"),
        bin=bin_,
        is_active=True,
    )
    db.add(partner)
    db.flush()
    return partner

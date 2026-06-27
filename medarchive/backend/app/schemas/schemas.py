"""Pydantic response/request schemas (brief §11). Documented in OpenAPI at /docs."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Services ──────────────────────────────────────────────────────────────────
class ServiceOut(ORMModel):
    service_id: str
    service_name: str
    category: str
    source_code: str | None = None
    tariff_code: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    icd_code: str | None = None
    is_active: bool = True


class ServiceListOut(BaseModel):
    total: int
    items: list[ServiceOut]


# ── Partners ──────────────────────────────────────────────────────────────────
class PartnerOut(ORMModel):
    partner_id: str
    name: str
    city: str | None = None
    address: str | None = None
    bin: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool = True


class PartnerPriceOut(BaseModel):
    """A partner's price for a given service (for /services/{id}/partners)."""
    partner_id: str
    partner_name: str
    city: str | None = None
    address: str | None = None
    price_resident_kzt: Decimal | None = None
    price_nonresident_kzt: Decimal | None = None
    currency_original: str = "KZT"
    price_original: Decimal | None = None
    effective_date: date | None = None
    is_verified: bool = False


class PriceItemOut(ORMModel):
    item_id: str
    service_name_raw: str
    service_id: str | None = None
    service_name: str | None = None
    match_confidence: float | None = None
    match_method: str = "none"
    price_resident_kzt: Decimal | None = None
    price_nonresident_kzt: Decimal | None = None
    price_original: Decimal | None = None
    currency_original: str = "KZT"
    is_verified: bool = False
    effective_date: date | None = None
    is_active: bool = True


# ── Search ────────────────────────────────────────────────────────────────────
class SearchResult(BaseModel):
    services: list[ServiceOut]
    partners: list[PartnerOut]


# ── Review queue ──────────────────────────────────────────────────────────────
class ReviewItemOut(BaseModel):
    review_id: str
    item_id: str
    service_name_raw: str
    source_fragment: str | None = None
    partner_name: str | None = None
    price_resident_kzt: Decimal | None = None
    price_nonresident_kzt: Decimal | None = None
    candidates: list[dict] = Field(default_factory=list)
    specialty_hint: str | None = None
    status: str = "open"


class MatchRequest(BaseModel):
    item_id: str
    service_id: str | None = Field(
        default=None, description="Target canonical service; omit when creating a new one."
    )
    new_service_name: str | None = Field(
        default=None, description="Create a new directory entry with this name."
    )
    new_service_category: str | None = None
    reject: bool = Field(default=False, description="Reject the row (no match).")
    note: str | None = None


class MatchResponse(BaseModel):
    item_id: str
    service_id: str | None
    match_method: str
    is_verified: bool
    learned_synonym: str | None = None
    message: str


# ── Jobs ──────────────────────────────────────────────────────────────────────
class JobOut(ORMModel):
    job_id: str
    archive_name: str | None = None
    status: str
    total_files: int = 0
    processed_files: int = 0
    error_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ── Price history ─────────────────────────────────────────────────────────────
class PriceHistoryEntry(BaseModel):
    item_id: str
    partner_id: str
    partner_name: str | None = None
    price_resident_kzt: Decimal | None = None
    price_nonresident_kzt: Decimal | None = None
    effective_date: date | None = None
    is_active: bool
    superseded_by: str | None = None


class PriceHistoryOut(BaseModel):
    service_id: str
    service_name: str
    entries: list[PriceHistoryEntry]

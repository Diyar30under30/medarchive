"""Validation rules + currency conversion tests (brief §9, §18) — positive/negative."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.validation.currency import to_kzt, rate_for
from app.validation.rules import RowToValidate, validate_row


def _row(**kw):
    base = dict(
        service_name_raw="Глюкоза",
        price_resident_kzt=Decimal("1500"),
        price_nonresident_kzt=Decimal("2100"),
        effective_date=date(2024, 1, 1),
    )
    base.update(kw)
    return RowToValidate(**base)


def test_empty_name_skips():
    res = validate_row(_row(service_name_raw="  "))
    assert res.should_skip


def test_valid_row_passes():
    res = validate_row(_row())
    assert not res.should_skip and not res.needs_review


def test_missing_price_needs_review():
    res = validate_row(_row(price_resident_kzt=None))
    assert res.needs_review
    assert any(f.code == "missing_price" for f in res.findings)


def test_nonresident_less_than_resident_flagged():
    res = validate_row(_row(price_nonresident_kzt=Decimal("1000")))
    assert any(f.code == "nonresident_lt_resident" for f in res.findings)


def test_future_date_warning():
    res = validate_row(_row(effective_date=date(2099, 1, 1)))
    assert any(f.code == "future_date" for f in res.findings)


def test_price_jump_anomaly():
    res = validate_row(_row(price_resident_kzt=Decimal("5000"),
                            previous_resident_kzt=Decimal("1500")))
    assert res.has_anomaly
    assert any(f.code == "price_jump" for f in res.findings)


def test_small_price_change_not_anomaly():
    res = validate_row(_row(price_resident_kzt=Decimal("1600"),
                            previous_resident_kzt=Decimal("1500")))
    assert not res.has_anomaly


# ── currency ──────────────────────────────────────────────────────────────────
def test_kzt_is_identity():
    assert to_kzt(1000, "KZT") == Decimal("1000.00")


def test_usd_converts_and_keeps_date_rate():
    v = to_kzt(100, "USD", date(2024, 1, 15))
    assert v == (Decimal("100") * rate_for("USD", date(2024, 1, 15))).quantize(Decimal("0.01"))
    assert v > 0


def test_non_numeric_returns_none():
    assert to_kzt("n/a", "KZT") is None
    assert to_kzt(None, "USD") is None

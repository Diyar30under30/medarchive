"""Offline currency conversion (brief §9).

A small configurable per-date rate table with a static fallback so conversion
runs with no network. Always returns KZT; callers keep price_original +
currency_original alongside.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

# Fallback rates → KZT (approximate, offline). Keyed by currency.
_FALLBACK_RATES: dict[str, Decimal] = {
    "KZT": Decimal("1"),
    "USD": Decimal("470"),
    "RUB": Decimal("5.2"),
}

# Optional per-date overrides: {currency: [(effective_from, rate), ...]} sorted asc.
_DATED_RATES: dict[str, list[tuple[date, Decimal]]] = {
    "USD": [
        (date(2024, 1, 1), Decimal("450")),
        (date(2024, 3, 1), Decimal("460")),
        (date(2025, 1, 1), Decimal("520")),
    ],
    "RUB": [
        (date(2024, 1, 1), Decimal("5.0")),
        (date(2025, 1, 1), Decimal("5.5")),
    ],
}


def rate_for(currency: str, on: date | None = None) -> Decimal:
    currency = (currency or "KZT").upper()
    if currency == "KZT":
        return Decimal("1")
    if on is not None and currency in _DATED_RATES:
        applicable = Decimal("0")
        for eff_from, r in _DATED_RATES[currency]:
            if eff_from <= on:
                applicable = r
        if applicable > 0:
            return applicable
    return _FALLBACK_RATES.get(currency, Decimal("1"))


def to_kzt(amount, currency: str, on: date | None = None) -> Decimal | None:
    """Convert an amount in `currency` to KZT. Returns None for non-numeric input."""
    if amount is None or amount == "":
        return None
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return (value * rate_for(currency, on)).quantize(Decimal("0.01"))

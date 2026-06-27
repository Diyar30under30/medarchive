"""Validation rules applied to each extracted/normalized row (brief §9).

Each rule is a small pure function returning ValidationFinding(s); the engine
runs them and produces flags the pipeline uses to set is_verified / needs_review
/ skip / anomaly. Pure and unit-testable (no DB).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

# Severity → pipeline meaning
SKIP = "skip"          # row not stored
REVIEW = "review"      # store but needs_review
ANOMALY = "anomaly"    # store, flag, require manual confirm
WARNING = "warning"    # store, note only


@dataclass
class Finding:
    code: str
    severity: str
    message: str


@dataclass
class RowToValidate:
    service_name_raw: str
    price_resident_kzt: Decimal | None
    price_nonresident_kzt: Decimal | None
    effective_date: date | None
    currency_original: str = "KZT"
    previous_resident_kzt: Decimal | None = None  # latest prior version, if any


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def should_skip(self) -> bool:
        return any(f.severity == SKIP for f in self.findings)

    @property
    def needs_review(self) -> bool:
        return any(f.severity in (REVIEW, ANOMALY) for f in self.findings)

    @property
    def has_anomaly(self) -> bool:
        return any(f.severity == ANOMALY for f in self.findings)

    @property
    def note(self) -> str:
        return "; ".join(f"{f.code}:{f.message}" for f in self.findings)


def validate_row(row: RowToValidate, *, today: date | None = None) -> ValidationResult:
    today = today or date.today()
    res = ValidationResult()

    # Service name not empty → skip row.
    if not (row.service_name_raw or "").strip():
        res.findings.append(Finding("empty_name", SKIP, "service name is empty"))
        return res  # nothing else matters

    # Price present, numeric, > 0 → review if not.
    pr = row.price_resident_kzt
    if pr is None:
        res.findings.append(Finding("missing_price", REVIEW, "resident price missing/non-numeric"))
    elif pr <= 0:
        res.findings.append(Finding("nonpositive_price", REVIEW, f"resident price {pr} <= 0"))

    # Non-resident >= resident (else flag for review).
    nr = row.price_nonresident_kzt
    if pr is not None and nr is not None and nr < pr:
        res.findings.append(
            Finding("nonresident_lt_resident", REVIEW,
                    f"non-resident {nr} < resident {pr}")
        )

    # Effective date not in the future (warning).
    if row.effective_date and row.effective_date > today:
        res.findings.append(
            Finding("future_date", WARNING, f"effective_date {row.effective_date} in future")
        )

    # Price differs > 50% from previous version → anomaly, manual confirm.
    prev = row.previous_resident_kzt
    if prev is not None and prev > 0 and pr is not None and pr > 0:
        change = abs(pr - prev) / prev
        if change > Decimal("0.5"):
            res.findings.append(
                Finding("price_jump", ANOMALY,
                        f"resident price changed {change:.0%} vs previous ({prev}→{pr})")
            )

    return res

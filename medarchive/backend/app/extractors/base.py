"""Extractor contract + registry (brief §3, §7).

Every extractor takes a file path and returns a uniform list[ExtractedRow].
New formats register via @register(...) and the dispatcher looks them up by
FileFormat — adding a format never touches the core (extensibility requirement).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from app.models.enums import FileFormat


@dataclass
class ExtractedRow:
    service_name_raw: str
    price_resident: str | float | None = None
    price_nonresident: str | float | None = None
    currency: str = "KZT"
    service_code_source: str | None = None
    specialty_hint: str | None = None       # from section/sheet/title context
    source_fragment: str | None = None       # snippet shown in the review queue
    raw_extra: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    rows: list[ExtractedRow]
    raw_text: str                            # preserved on the document (audit)
    log: str = ""                            # human-readable extraction notes


class Extractor(Protocol):
    def extract(self, path: Path) -> ExtractionResult: ...


_REGISTRY: dict[FileFormat, "Extractor"] = {}


def register(fmt: FileFormat) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        _REGISTRY[fmt] = cls()
        return cls
    return deco


def get_extractor(fmt: FileFormat) -> "Extractor":
    if fmt not in _REGISTRY:
        raise KeyError(f"No extractor registered for format {fmt!r}")
    return _REGISTRY[fmt]


def registered_formats() -> list[FileFormat]:
    return list(_REGISTRY)


# Helpers shared by extractors ────────────────────────────────────────────────
_HEADER_HINTS = (
    "наименование", "услуга", "услуги", "цена", "стоимость",
    "резидент", "нерезидент", "тариф", "прайс", "қызмет", "бағасы",
)
_PRICE_HINTS_RES = ("резидент", "резид", "цена", "стоимость", "бағас")
_PRICE_HINTS_NONRES = ("нерезидент", "нерезид")


def looks_like_header(cells: list) -> bool:
    text = " ".join(str(c).lower() for c in cells if c is not None)
    return sum(h in text for h in _HEADER_HINTS) >= 1


def classify_columns(headers: list) -> dict:
    """Map a header row to {name, resident, nonresident} column indices (best effort)."""
    cols = {"name": None, "resident": None, "nonresident": None}
    for i, h in enumerate(headers):
        t = str(h).lower() if h is not None else ""
        if cols["name"] is None and ("наимен" in t or "услуг" in t or "қызмет" in t):
            cols["name"] = i
        elif any(k in t for k in _PRICE_HINTS_NONRES):
            cols["nonresident"] = i
        elif any(k in t for k in _PRICE_HINTS_RES):
            if cols["resident"] is None:
                cols["resident"] = i
            elif cols["nonresident"] is None:
                cols["nonresident"] = i
    return cols

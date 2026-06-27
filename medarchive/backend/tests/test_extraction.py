"""Extraction tests (brief §18): generate one fixture per format in-memory and
assert the extractor recovers rows, incl. DOCX tracked-changes resolution."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.extractors import get_extractor  # registers all extractors
from app.models.enums import FileFormat
from scripts._fixture_data import CLINICS
from scripts import generate_fixtures as gf


CLINIC = CLINICS[0]
ROWS = [
    {"raw": "ОАК", "canonical": "Общий анализ крови", "specialty_hint": None,
     "resident": 1500, "nonresident": 2100, "currency": "KZT"},
    {"raw": "Глюкоза", "canonical": "Глюкоза", "specialty_hint": None,
     "resident": 1200, "nonresident": 1600, "currency": "KZT"},
]


def _write(tmp: Path, name: str, data: bytes) -> Path:
    p = tmp / name
    p.write_bytes(data)
    return p


def test_xlsx_extracts_rows(tmp_path):
    p = _write(tmp_path, "x.xlsx", gf.write_xlsx(CLINIC, ROWS, header_offset=1))
    res = get_extractor(FileFormat.xlsx).extract(p)
    names = [r.service_name_raw for r in res.rows]
    assert "ОАК" in names and "Глюкоза" in names
    assert "Клиника" in res.raw_text  # metadata preserved for partner parsing


def test_docx_resolves_tracked_changes(tmp_path):
    p = _write(tmp_path, "d.docx", gf.write_docx_tracked(CLINIC, ROWS))
    res = get_extractor(FileFormat.docx).extract(p)
    names = [r.service_name_raw for r in res.rows]
    assert "ОАК" in names
    # The tracked-DELETED price 999999 must NOT survive into any extracted value.
    joined = " ".join(f"{r.price_resident}" for r in res.rows)
    assert "999999" not in joined
    assert "999999" not in res.raw_text


@pytest.mark.skipif(gf._cyrillic_fontfile() is None, reason="no Cyrillic font available")
def test_pdf_text_extracts_rows(tmp_path):
    p = _write(tmp_path, "p.pdf", gf.write_pdf_text(CLINIC, ROWS))
    res = get_extractor(FileFormat.pdf).extract(p)
    names = " ".join(r.service_name_raw for r in res.rows)
    assert "ОАК" in names or "Глюкоза" in names


def test_registry_has_all_formats():
    from app.extractors.base import registered_formats

    for fmt in (FileFormat.pdf, FileFormat.scan_pdf, FileFormat.xlsx, FileFormat.docx):
        assert fmt in registered_formats()

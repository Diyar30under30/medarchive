"""Reference-loader tests (ТЗ §2.2): the loader must handle the organizer-spec
directory schema (service_id, service_name, synonyms, category, icd_code) in both
XLSX and JSON, load provided synonyms/icd_code, and merge on re-load."""
from __future__ import annotations

import io
import json

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.service import Service
from app.normalization.matcher import Matcher, ServiceIndex
from app.normalization.reference_loader import load_reference

# Organizer-spec rows (ТЗ §2.2): note synonyms as an array and an icd_code.
TZ_ROWS = [
    {"service_id": "svc-001", "service_name": "Общий анализ крови",
     "synonyms": ["ОАК", "CBC", "клинический анализ крови"], "category": "Лаборатория", "icd_code": "Z00.0"},
    {"service_id": "svc-002", "service_name": "Глюкоза крови",
     "synonyms": ["сахар крови", "глюкоза"], "category": "Лаборатория", "icd_code": ""},
    {"service_id": "svc-003", "service_name": "УЗИ щитовидной железы",
     "synonyms": [], "category": "Диагностика", "icd_code": ""},
]


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _write_tz_xlsx(tmp_path):
    wb = Workbook()
    ws = wb.active
    headers = ["service_id", "service_name", "synonyms", "category", "icd_code"]
    ws.append(headers)
    for r in TZ_ROWS:
        ws.append([r["service_id"], r["service_name"], json.dumps(r["synonyms"], ensure_ascii=False),
                   r["category"], r["icd_code"]])
    p = tmp_path / "Справочник.xlsx"
    wb.save(p)
    return p


def test_loads_tz_schema_xlsx(db, tmp_path):
    res = load_reference(db, _write_tz_xlsx(tmp_path))
    assert res["total"] == 3
    assert res["with_provided_synonyms"] == 2
    assert res["columns"].get("synonyms") == "synonyms"

    oak = db.get(Service, "svc-001")
    assert oak is not None  # provided service_id used verbatim
    assert oak.icd_code == "Z00.0"
    assert "оак" in oak.synonyms or "ОАК" in oak.synonyms or "cbc" in [s.lower() for s in oak.synonyms]


def test_loads_tz_schema_json(db, tmp_path):
    p = tmp_path / "dir.json"
    p.write_text(json.dumps({"services": TZ_ROWS}, ensure_ascii=False), encoding="utf-8")
    res = load_reference(db, p)
    assert res["total"] == 3
    assert db.get(Service, "svc-002").service_name == "Глюкоза крови"


def test_provided_synonyms_drive_auto_match(db, tmp_path):
    load_reference(db, _write_tz_xlsx(tmp_path))
    rows = [{"service_id": s.service_id, "service_name": s.service_name,
             "category": s.category, "synonyms": s.synonyms, "embedding": None}
            for s in db.scalars(select(Service)).all()]
    matcher = Matcher(ServiceIndex.from_rows(rows))
    # "CBC" is a provided synonym of Общий анализ крови → exact synonym match (1.0).
    cands = matcher.match("CBC")
    assert cands and cands[0].service_id == "svc-001"
    assert cands[0].score == 1.0


def test_reload_merges_synonyms(db, tmp_path):
    p = _write_tz_xlsx(tmp_path)
    load_reference(db, p)
    svc = db.get(Service, "svc-003")
    svc.synonyms = ["узи щитовидки"]  # operator-learned
    db.commit()
    # Re-load the directory (now with a provided synonym for svc-003).
    TZ_ROWS[2]["synonyms"] = ["УЗИ ЩЖ"]
    load_reference(db, _write_tz_xlsx(tmp_path))
    db.refresh(svc)
    assert "узи щитовидки" in svc.synonyms          # learned synonym preserved
    assert "УЗИ ЩЖ" in svc.synonyms                  # provided synonym added
    TZ_ROWS[2]["synonyms"] = []  # restore for other tests

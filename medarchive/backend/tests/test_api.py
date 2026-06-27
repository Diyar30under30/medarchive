"""API smoke + behavior tests (brief §18). Uses an isolated SQLite DB, loads the
synthetic directory, ingests the fixtures, then exercises every endpoint."""
from __future__ import annotations

import os
import tempfile

import pytest

# Isolate the test DB before app modules read settings.
_TMP = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AUTO_LOAD_REFERENCE"] = "false"
os.environ["AUTO_SEED_FIXTURES"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  (register entities; keep before the alias)
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402  (alias: 'app' is the package)


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    # Seed: synthetic directory + ingested fixtures.
    from scripts.generate_reference import main as gen_ref
    from scripts.generate_fixtures import main as gen_fix
    from app.normalization.reference_loader import load_reference
    from app.workers.jobs import create_job, run_job

    ref_path = gen_ref()
    with SessionLocal() as db:
        load_reference(db, ref_path)
    zip_path = gen_fix()
    with SessionLocal() as db:
        job = create_job(db, zip_path.name)
        job_id = job.job_id
    run_job(job_id, str(zip_path))

    with TestClient(fastapi_app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_documented(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for p in ["/services", "/search", "/partners", "/unmatched", "/match",
              "/admin/ingest", "/metrics"]:
        assert p in paths, f"{p} missing from OpenAPI"


def test_list_services(client):
    r = client.get("/services", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 100
    assert len(body["items"]) == 5


def test_search_abbreviation(client):
    r = client.get("/search", params={"q": "Глюкоза"})
    assert r.status_code == 200
    assert any("Глюкоза" in s["service_name"] for s in r.json()["services"])


def test_partners_listed(client):
    r = client.get("/partners")
    assert r.status_code == 200
    assert len(r.json()) >= 5


def test_metrics_headline(client):
    m = client.get("/metrics").json()
    assert m["positions_total"] > 0
    assert m["auto_normalization_rate"] >= 0.70  # target
    assert "matches_by_method" in m


def test_review_queue_and_manual_match(client):
    queue = client.get("/unmatched").json()
    assert isinstance(queue, list)
    if queue:
        item = queue[0]
        # confirm against the first candidate (or skip if none)
        cands = item["candidates"]
        if cands:
            resp = client.post("/match", json={
                "item_id": item["item_id"],
                "service_id": cands[0]["service_id"],
            })
            assert resp.status_code == 200
            assert resp.json()["is_verified"] is True


def test_service_partners_and_history(client):
    svc = client.get("/services", params={"limit": 1}).json()["items"][0]
    r = client.get(f"/services/{svc['service_id']}/partners")
    assert r.status_code == 200
    h = client.get(f"/services/{svc['service_id']}/price-history")
    assert h.status_code == 200


def test_anomalies_listed(client):
    r = client.get("/anomalies")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and len(rows) > 0
    assert {"kind", "note", "partner_name"} <= set(rows[0])


def test_export_csv_and_xlsx(client):
    csv = client.get("/export.csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert "partner" in csv.text.splitlines()[0]
    xlsx = client.get("/export.xlsx")
    assert xlsx.status_code == 200
    assert len(xlsx.content) > 0

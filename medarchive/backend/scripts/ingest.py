"""CLI ingest — identical behavior to POST /admin/ingest (brief §14).

Usage: python -m scripts.ingest data/incoming/sample_archive.zip
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.workers.jobs import create_job, run_job
import app.models  # noqa: F401


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m scripts.ingest <archive.zip>")
        return 2
    zip_path = Path(argv[1])
    if not zip_path.exists():
        print(f"archive not found: {zip_path}")
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        job = create_job(db, zip_path.name)
        job_id = job.job_id

    report = run_job(job_id, str(zip_path))
    g = report["global"]
    run = report["last_run"]
    print(f"\nIngest complete for {zip_path.name} (job {job_id})")
    print(f"  files: {run.get('processed_files')} processed, {run.get('errored_files')} errored")
    print(f"  positions: {g['positions_total']} "
          f"(auto {g['auto_matched']}, review {g['review_queue_open']}, unmatched {g['unmatched']})")
    print(f"  auto-normalization: {g['auto_normalization_rate']:.1%}")
    print(f"  anomalies flagged: {g['anomalies_flagged']}")
    print(f"  per-format: {g['per_format_success']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

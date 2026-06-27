"""Job execution (brief §7 step 10). Shared by the API (BackgroundTasks) and the
ingest CLI, so both code paths are identical."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.db.session import SessionLocal
from app.ingestion.pipeline import IngestCounters, process_archive
from app.models.enums import JobStatus
from app.models.job import Job
from app.reporting.quality import write_quality_report

log = logging.getLogger("medarchive.jobs")


def create_job(db, archive_name: str) -> Job:
    job = Job(archive_name=archive_name, status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_job(job_id: str, zip_path: str) -> dict:
    """Run an ingest end-to-end in its own session (safe for BackgroundTasks)."""
    path = Path(zip_path)
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            job = Job(job_id=job_id, archive_name=path.name)
            db.add(job)
        job.status = JobStatus.processing
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        def _progress(c: IngestCounters) -> None:
            job.total_files = c.total_files
            job.processed_files = c.processed_files
            job.error_count = c.errored_files
            db.commit()

        try:
            counters = process_archive(db, path, on_progress=_progress)
            job.status = JobStatus.done
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s failed", job_id)
            counters = IngestCounters()
            job.status = JobStatus.error
            job.error_count += 1
        finally:
            job.total_files = counters.total_files
            job.processed_files = counters.processed_files
            job.error_count = counters.errored_files
            job.finished_at = datetime.now(timezone.utc)
            db.commit()

        report = write_quality_report(db, counters, archive_name=path.name)
    return report

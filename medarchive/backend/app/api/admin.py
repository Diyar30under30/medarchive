"""Admin endpoints: archive ingest + job status (brief §11)."""
from __future__ import annotations

import shutil

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.job import Job
from app.schemas.schemas import JobOut
from app.workers.jobs import create_job, run_job

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest", response_model=JobOut, status_code=202)
def ingest(
    background: BackgroundTasks,
    file: UploadFile = File(..., description="ZIP archive of partner price lists"),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "expected a .zip archive")

    settings.incoming_path.mkdir(parents=True, exist_ok=True)
    dest = settings.incoming_path / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = create_job(db, file.filename)
    # Run in the background so the upload returns immediately (brief §7 step 10).
    background.add_task(run_job, job.job_id, str(dest))
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobOut.model_validate(job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = 20):
    from sqlalchemy import select

    rows = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)).all()
    return [JobOut.model_validate(j) for j in rows]

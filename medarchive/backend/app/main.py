"""MedArchive API entrypoint.

A0: serves OpenAPI docs at /docs and a health check. Later phases register the
resource routers and wire startup (reference load, fixture seed).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("medarchive")


def init_db() -> None:
    """Create tables from the registered models (idempotent).

    Importing app.models registers every entity on Base.metadata. In the Docker
    profile Alembic owns the schema; create_all is a safe no-op there because the
    tables already exist, and it makes the SQLite dev profile zero-setup.
    """
    from app.db.base import Base
    from app.db.session import engine

    try:
        import app.models  # noqa: F401  (registers entities)
    except ModuleNotFoundError:
        log.info("No models package yet — skipping table creation.")
        return
    Base.metadata.create_all(bind=engine)
    log.info("Database tables ensured (%s).", "postgres" if settings.is_postgres else "sqlite")


def startup_data() -> None:
    """Best-effort: load the directory and optionally seed fixtures on boot.
    Never crashes the server — the API must always come up so /docs is reachable."""
    from app.db.session import SessionLocal

    if settings.auto_load_reference:
        try:
            from app.normalization.reference_loader import find_reference_file, load_reference

            path = find_reference_file()
            if path is None:
                from scripts.generate_reference import main as gen
                path = gen()
            with SessionLocal() as db:
                result = load_reference(db, path)
            log.info("Reference loaded: %s", result)
        except Exception:  # noqa: BLE001
            log.exception("Reference load skipped (continuing).")

    if settings.auto_seed_fixtures:
        try:
            from pathlib import Path

            from scripts.generate_fixtures import main as gen_fix
            from app.workers.jobs import create_job, run_job

            zip_path = settings.incoming_path / "sample_archive.zip"
            if not zip_path.exists():
                gen_fix()
            with SessionLocal() as db:
                from sqlalchemy import func, select
                from app.models.price_item import PriceItem

                already = db.scalar(select(func.count()).select_from(PriceItem)) or 0
            if already == 0:
                with SessionLocal() as db:
                    job = create_job(db, zip_path.name)
                    job_id = job.job_id
                run_job(job_id, str(zip_path))
                log.info("Seeded fixtures from %s", zip_path)
        except Exception:  # noqa: BLE001
            log.exception("Fixture seed skipped (continuing).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "Starting MedArchive %s | db=%s | embeddings=%s | ocr=%s",
        __version__,
        "postgres" if settings.is_postgres else "sqlite",
        settings.enable_embeddings,
        settings.enable_ocr,
    )
    init_db()
    startup_data()
    yield
    log.info("Shutting down MedArchive.")


app = FastAPI(
    title="MedArchive API",
    version=__version__,
    description=(
        "Normalize a clinic price-list archive into a verified, queryable database "
        "of services and partner prices. OpenAPI docs below."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe used by docker-compose and uptime checks."""
    return {
        "status": "ok",
        "version": __version__,
        "database": "postgres" if settings.is_postgres else "sqlite",
        "embeddings": settings.enable_embeddings,
        "ocr": settings.enable_ocr,
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "MedArchive", "version": __version__, "docs": "/docs"}


# Resource routers are included here as each phase lands them.
def _register_routers() -> None:
    try:
        from app.api import register_routers
    except ModuleNotFoundError:
        return
    register_routers(app)


_register_routers()

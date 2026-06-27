"""API routers. register_routers(app) attaches every resource router.

Routers are added here as each phase lands (A6 wires the full set from brief §11).
"""
from __future__ import annotations

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    from app.api import admin, analytics, metrics, partners, review, search, services

    app.include_router(services.router)
    app.include_router(partners.router)
    app.include_router(search.router)
    app.include_router(review.router)
    app.include_router(admin.router)
    app.include_router(metrics.router)
    app.include_router(analytics.router)

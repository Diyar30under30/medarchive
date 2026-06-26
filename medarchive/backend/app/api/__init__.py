"""API routers. register_routers(app) attaches every resource router.

Routers are added here as each phase lands (A6 wires the full set from brief §11).
"""
from __future__ import annotations

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    # from app.api import services, partners, search, admin, ...
    # app.include_router(services.router)
    return

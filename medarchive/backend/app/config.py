"""Centralized configuration — the single place the two-profile runtime is decided.

Everything that differs between the host SQLite dev profile and the Docker
Postgres+pgvector profile is a setting here, driven by environment variables
(see .env.example). Nothing else in the codebase reads os.environ directly.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (this file is backend/app/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./medarchive.db"

    # ── Feature flags (graceful degradation) ────────────────────────────────
    enable_embeddings: bool = False
    enable_ocr: bool = False

    # ── Startup behavior ────────────────────────────────────────────────────
    auto_load_reference: bool = True
    auto_seed_fixtures: bool = False

    # ── Matching engine ─────────────────────────────────────────────────────
    match_fusion_lexical: float = 0.45
    match_fusion_semantic: float = 0.55
    match_threshold_auto: float = 0.85
    match_threshold_review: float = 0.65
    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    # ── Paths ───────────────────────────────────────────────────────────────
    reference_dir: str = "../data/reference"
    incoming_dir: str = "../data/incoming"
    raw_store_dir: str = "../data/raw_store"

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Derived helpers ─────────────────────────────────────────────────────
    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolve(self, relative: str) -> Path:
        """Resolve a configured path relative to the backend dir, absolute-safe."""
        p = Path(relative)
        return p if p.is_absolute() else (BACKEND_DIR / p).resolve()

    @property
    def reference_path(self) -> Path:
        return self.resolve(self.reference_dir)

    @property
    def incoming_path(self) -> Path:
        return self.resolve(self.incoming_dir)

    @property
    def raw_store_path(self) -> Path:
        return self.resolve(self.raw_store_dir)

    @field_validator("match_fusion_semantic")
    @classmethod
    def _weights_sane(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("match_fusion_semantic must be in [0, 1]")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

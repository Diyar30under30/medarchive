"""CLI: load the canonical directory into the DB (idempotent).

Generates a synthetic directory first if none is present, so a fresh checkout
has something to load. Run: python -m scripts.load_reference [path]
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.normalization.reference_loader import find_reference_file, load_reference
import app.models  # noqa: F401  (register entities)


def main(argv: list[str]) -> int:
    Base.metadata.create_all(bind=engine)

    path = Path(argv[1]) if len(argv) > 1 else find_reference_file()
    if path is None:
        print("No reference file found — generating a synthetic directory…")
        from scripts.generate_reference import main as gen
        path = gen()

    with SessionLocal() as db:
        result = load_reference(db, path)
    print(
        f"Reference loaded: {result['loaded']} new, {result['updated']} updated, "
        f"{result['skipped']} skipped (total {result.get('total', 0)}), "
        f"embeddings={result['embeddings']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

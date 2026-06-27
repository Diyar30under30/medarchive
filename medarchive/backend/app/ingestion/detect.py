"""Format detection (brief §7 step 2).

Extension + magic bytes, and for PDFs a text-layer probe to split true text PDFs
from image-only scans that must go to OCR.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.models.enums import FileFormat

log = logging.getLogger("medarchive.detect")


def _magic(path: Path, n: int = 8) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def has_text_layer(path: Path, min_chars: int = 20) -> bool:
    """True if the PDF has an extractable text layer (→ text PDF, not a scan)."""
    try:
        import fitz

        doc = fitz.open(path)
        chars = 0
        for page in doc:
            chars += len((page.get_text() or "").strip())
            if chars >= min_chars:
                doc.close()
                return True
        doc.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("text-layer probe failed for %s: %s", path.name, exc)
    return False


def detect_format(path: Path) -> FileFormat:
    ext = path.suffix.lower()
    magic = _magic(path)

    if ext in (".xlsx", ".xls", ".xlsm") or magic[:2] == b"PK" and ext != ".docx":
        # ZIP-based; disambiguate docx vs xlsx by extension primarily.
        if ext == ".docx":
            return FileFormat.docx
        return FileFormat.xlsx
    if ext == ".docx":
        return FileFormat.docx
    if ext == ".pdf" or magic[:4] == b"%PDF":
        return FileFormat.scan_pdf if not has_text_layer(path) else FileFormat.pdf

    # Fallback by extension.
    if ext == ".docx":
        return FileFormat.docx
    if ext in (".xlsx", ".xls"):
        return FileFormat.xlsx
    return FileFormat.pdf  # best effort; extractor will log if it can't parse

"""Text-PDF extractor (brief §7).

pdfplumber tables first, PyMuPDF text as fallback. Tolerates two layouts:
structured tables (header → column map) and plain "name … price price" lines.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.extractors.base import (
    ExtractedRow,
    ExtractionResult,
    classify_columns,
    looks_like_header,
    register,
)
from app.models.enums import FileFormat

# Trailing 1–2 numeric tokens on a line = prices; the rest is the service name.
_PRICE_TOKEN = r"\d[\d  .,]*"
_LINE_RE = re.compile(rf"^(?P<name>.+?)\s+(?P<p1>{_PRICE_TOKEN})(?:\s+(?P<p2>{_PRICE_TOKEN}))?\s*$")


def _num(s: str | None):
    if not s:
        return None
    cleaned = s.replace(" ", "").replace(" ", "").replace(",", ".")
    cleaned = re.sub(r"\.(?=\d{3}\b)", "", cleaned)  # strip thousands dots
    try:
        return float(cleaned)
    except ValueError:
        return None


# Clinic-metadata / label lines that must not be parsed as price rows.
_LABEL_RE = re.compile(
    r"^\s*(клиника|город|адрес|тел(?:ефон)?|phone|бин|қала|мекенжай|прайс|услуга\s*/)\b",
    re.IGNORECASE,
)


def parse_price_line(line: str) -> ExtractedRow | None:
    line = line.strip()
    if not line or looks_like_header([line]) or _LABEL_RE.match(line):
        return None
    m = _LINE_RE.match(line)
    if not m:
        return None
    name = m.group("name").strip(" .|—-")
    if len(name) < 2 or name.replace(" ", "").isdigit():
        return None
    return ExtractedRow(
        service_name_raw=name,
        price_resident=_num(m.group("p1")),
        price_nonresident=_num(m.group("p2")),
        source_fragment=line[:200],
    )


@register(FileFormat.pdf)
class PdfTextExtractor:
    def extract(self, path: Path) -> ExtractionResult:
        rows: list[ExtractedRow] = []
        text_parts: list[str] = []
        notes: list[str] = []

        used_tables = False
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                for pi, page in enumerate(pdf.pages):
                    text_parts.append(page.extract_text() or "")
                    for table in page.extract_tables() or []:
                        if self._consume_table(table, rows):
                            used_tables = True
            if used_tables:
                notes.append("parsed via pdfplumber tables")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"pdfplumber failed: {exc}")

        # Fallback / line layout: parse text lines for prices.
        if not rows:
            full_text = "\n".join(text_parts)
            if not full_text.strip():
                full_text = self._pymupdf_text(path, notes)
                text_parts = [full_text]
            for line in full_text.splitlines():
                row = parse_price_line(line)
                if row:
                    rows.append(row)
            notes.append(f"parsed {len(rows)} line(s) from text layer")

        return ExtractionResult(
            rows=rows, raw_text="\n".join(text_parts), log="; ".join(notes)
        )

    @staticmethod
    def _consume_table(table: list[list], rows: list[ExtractedRow]) -> bool:
        if not table or len(table) < 2:
            return False
        header_idx = next(
            (i for i, r in enumerate(table[:4]) if r and looks_like_header(r)), None
        )
        if header_idx is None:
            return False
        cols = classify_columns(table[header_idx])
        if cols["name"] is None:
            cols["name"] = 0
        added = 0
        for r in table[header_idx + 1:]:
            name = (r[cols["name"]] or "").strip() if cols["name"] < len(r) else ""
            if not name:
                continue
            res = r[cols["resident"]] if cols["resident"] is not None and cols["resident"] < len(r) else None
            nonres = r[cols["nonresident"]] if cols["nonresident"] is not None and cols["nonresident"] < len(r) else None
            rows.append(
                ExtractedRow(
                    service_name_raw=name,
                    price_resident=_num(res) if isinstance(res, str) else res,
                    price_nonresident=_num(nonres) if isinstance(nonres, str) else nonres,
                    source_fragment=" | ".join(str(c) for c in r if c)[:200],
                )
            )
            added += 1
        return added > 0

    @staticmethod
    def _pymupdf_text(path: Path, notes: list[str]) -> str:
        try:
            import fitz

            doc = fitz.open(path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as exc:  # noqa: BLE001
            notes.append(f"pymupdf text failed: {exc}")
            return ""

"""Scanned-PDF extractor with OCR (brief §7).

Rasterizes pages with PyMuPDF and OCRs them with Tesseract (rus+kaz+eng), then
post-processes artifacts and reuses the text-line parser. OCR is feature-flagged:
when Tesseract/pytesseract is unavailable (host dev), it degrades gracefully —
the document is logged and routed to review rather than crashing the batch.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.config import settings
from app.extractors.base import ExtractedRow, ExtractionResult, register
from app.extractors.pdf_text import parse_price_line
from app.models.enums import FileFormat

# Common OCR artifact fixes before parsing.
_OCR_FIXES = [
    (re.compile(r"[«»“”]"), '"'),
    (re.compile(r"[│|]"), " "),
    (re.compile(r"(?<=\d)[oOоО](?=\d)"), "0"),   # letter-O between digits → 0
    (re.compile(r"[ \t]{2,}"), " "),
]


def postprocess_ocr(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        s = line
        for rx, rep in _OCR_FIXES:
            s = rx.sub(rep, s)
        s = s.strip()
        if s:
            out_lines.append(s)
    return "\n".join(out_lines)


@register(FileFormat.scan_pdf)
class PdfScanOcrExtractor:
    def extract(self, path: Path) -> ExtractionResult:
        notes: list[str] = []

        if not settings.enable_ocr:
            notes.append("OCR disabled (ENABLE_OCR=false) — routed to review")
            return ExtractionResult(rows=[], raw_text="", log="; ".join(notes))

        try:
            import fitz
            import pytesseract  # noqa: F401
            from PIL import Image
        except Exception as exc:  # noqa: BLE001
            notes.append(f"OCR deps unavailable ({exc}) — routed to review")
            return ExtractionResult(rows=[], raw_text="", log="; ".join(notes))

        import io

        import pytesseract
        from PIL import Image

        raw_text_parts: list[str] = []
        try:
            doc = fitz.open(path)
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                txt = pytesseract.image_to_string(img, lang="rus+kaz+eng")
                raw_text_parts.append(txt)
            doc.close()
        except Exception as exc:  # noqa: BLE001
            notes.append(f"OCR failed: {exc}")
            return ExtractionResult(rows=[], raw_text="\n".join(raw_text_parts), log="; ".join(notes))

        text = postprocess_ocr("\n".join(raw_text_parts))
        rows: list[ExtractedRow] = []
        for line in text.splitlines():
            row = parse_price_line(line)
            if row:
                rows.append(row)
        notes.append(f"OCR extracted {len(rows)} row(s)")
        return ExtractionResult(rows=rows, raw_text=text, log="; ".join(notes))

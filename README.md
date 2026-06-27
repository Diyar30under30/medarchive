# MedArchive

Turns a messy archive of clinic price lists — **text PDF, scanned PDF, XLSX, and DOCX
with tracked changes** — into a clean, **verified, queryable database** of *who provides
which medical service and at what price*, normalized to a single canonical service
directory. Built for a 2025 hackathon (case: automated processing of a clinic price-list
archive).

> **The app lives in [`medarchive/`](medarchive/) — see its [README](medarchive/README.md)
> for full setup, architecture, and how to swap in the organizers' real data.**

## What it does

```
ZIP archive ─► unzip ─► format detect ─► extractor (pdf / scan-OCR / xlsx / docx-tracked)
           ─► normalize → match to canonical directory (lexical + semantic + fusion)
           ─► validate (price / currency / anomaly / dup) ─► version (supersede prior)
           ─► persist ─► quality report + operator verification queue
```

Three surfaces: an **ingestion pipeline**, a **public search** (find a service → compare
partner prices), and an **operator console** (upload, a keyboard-first verification queue,
and a dashboard headlining the **% auto-normalized**).

## Highlights

- **94.6% auto-normalization** end-to-end on the synthetic archive (matcher alone 96.8%),
  well above the ≥70% target — even in host mode without the semantic model.
- **All four formats parse**; a deliberately broken file is logged without halting the batch.
- **Name normalization engine** (the graded core): preprocess + abbreviation map +
  exact/synonym + RapidFuzz lexical + multilingual embeddings + score fusion + specialty
  disambiguation + a **synonym-learning loop** that lifts the match rate as operators confirm.
- **Validation & versioning**: price anomalies flagged, currencies converted (originals kept),
  prices versioned never overwritten.
- **OpenAPI-documented REST API** (FastAPI) + **React/Vite/Tailwind** UI with live dashboard,
  price-history charts, anomaly view, and CSV/XLSX export.
- **Bilingual RU/KK** data handled throughout (Cyrillic + Kazakh).

## Stack

Python 3.11 · FastAPI · PostgreSQL + pgvector (or SQLite dev) · SQLAlchemy/Alembic ·
pdfplumber · PyMuPDF · Tesseract OCR · openpyxl · python-docx · RapidFuzz ·
sentence-transformers · React + Vite + TypeScript + Tailwind + Recharts · Docker Compose.

## Quick start

```bash
cd medarchive
docker compose up --build     # DB + API (:8000/docs) + frontend (:5173)
```

No Docker? A two-profile runtime also runs locally on SQLite — see
[medarchive/README.md](medarchive/README.md).

---

🤖 Built with [Claude Code](https://claude.com/claude-code).

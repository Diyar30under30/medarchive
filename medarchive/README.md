# MedArchive

Turn a messy archive of clinic price lists (text PDF, scanned PDF, XLSX, DOCX with
tracked changes) into a clean, queryable, **verified** database of *who provides which
medical service and at what price* — normalized to a single canonical service directory.

> Hackathon MVP. Built Part A (mandatory) first, end-to-end and runnable at every step.

## Quick start

### Option 1 — Docker (brief-compliant, judge-facing)

```bash
cd medarchive
cp .env.example .env          # defaults are fine
docker compose up --build     # → DB (Postgres+pgvector) + API + frontend
```

- API + Swagger: <http://localhost:8000/docs>
- Frontend: <http://localhost:5173>

The image bakes in Tesseract (`rus+kaz+eng`) and the multilingual embedding model, so
the system runs **fully offline** at judging time.

### Option 2 — Host dev (no Docker, SQLite)

Uses [`uv`](https://github.com/astral-sh/uv) to provision Python 3.12 with prebuilt wheels.

```bash
cd medarchive/backend
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --reload      # → :8000/docs

cd ../frontend
npm install && npm run dev                                      # → :5173
```

In host mode the matcher runs **lexical-only** (RapidFuzz) and OCR is off; both
activate automatically in the Docker profile. This is the two-profile runtime.

## Architecture

```
ZIP archive ─► unzip ─► format detect ─► extractor (pdf/scan/xlsx/docx)
           ─► normalize → match to canonical directory (lexical + semantic + fusion)
           ─► validate (price/currency/anomaly/dup) ─► version (supersede prior)
           ─► persist PriceItem ─► quality report + verification queue
```

See [design doc](../docs/superpowers/specs/2026-06-27-medarchive-design.md) for the full
architecture and the two-profile decision.

## Swapping in the real organizers' data

- **Reference directory:** drop `Справочник услуг.xlsx` (or a JSON with the same
  `ID | Специальность | Code | Name_ru | TarificatrCode` mapping) into `data/reference/`,
  then re-run `python -m scripts.load_reference` (idempotent).
- **Price-list archive:** drop the ZIP into `data/incoming/` and either
  `POST /admin/ingest` or `python -m scripts.ingest data/incoming/<archive>.zip`.

## Config knobs

All in `.env` (see `.env.example`): `DATABASE_URL`, `ENABLE_EMBEDDINGS`, `ENABLE_OCR`,
match fusion weights (`MATCH_FUSION_LEXICAL`/`SEMANTIC`), decision thresholds
(`MATCH_THRESHOLD_AUTO`/`REVIEW`), embedding model, data paths.

## Build status

| Phase | Scope | Status |
|---|---|---|
| A0 | Scaffold, docker compose, health, two-profile runtime | ✅ |
| A1 | Reference directory: models + loader (XLSX/JSON, UUIDs, embeddings) | ⏳ |
| A2 | Synthetic fixtures (4 formats, anomalies) | ⏳ |
| A3 | Ingestion + 4 extractors (incl. OCR, tracked changes) | ⏳ |
| A4 | Matching engine (lexical + semantic + fusion + learning loop) | ⏳ |
| A5 | Validation, currency, versioning | ⏳ |
| A6 | REST API (OpenAPI) | ⏳ |
| A7 | Frontend (search + operator console + dashboard) | ⏳ |
| A8 | Tests + quality report + README | ⏳ |

## Headline metric

After every ingest the system writes a quality report (`/metrics` + dashboard):
documents processed, **% auto-normalized**, review/unmatched counts, anomalies,
per-format success rates. Target: **≥70% auto-normalization**.

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

- **Reference directory:** drop the organizers' directory (XLSX **or** JSON) into
  `data/reference/`, then re-run `python -m scripts.load_reference` (idempotent).
  The loader is **schema-flexible** — it auto-detects columns by name and handles
  both the spec layout (`service_id, service_name, synonyms, category, icd_code`)
  and the real-file layout (`ID, Специальность, Code, Name_ru, TarificatrCode`).
  A provided `service_id` is used as-is (else a deterministic UUID5 is generated);
  provided `synonyms`/`icd_code` are loaded, and provided synonyms are **merged**
  with operator-learned ones on re-load so the learning loop is never lost.
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
| A1 | Reference directory: models + loader (XLSX/JSON, UUIDs, embeddings) | ✅ |
| A2 | Synthetic fixtures (4 formats, anomalies) | ✅ |
| A3 | Ingestion + 4 extractors (incl. OCR, tracked changes) | ✅ |
| A4 | Matching engine (lexical + semantic + fusion + learning loop) | ✅ |
| A5 | Validation, currency, versioning | ✅ |
| A6 | REST API (OpenAPI) | ✅ |
| A7 | Frontend (search + operator console + dashboard) | ✅ |
| A8 | Tests + quality report + README | ✅ |

## Verified results (host dev profile, lexical-only matching, OCR off)

- **Auto-normalization: 94.6%** end-to-end on the synthetic archive (53/56
  positions), **0 unmatched** — far above the ≥70% target. The standalone matcher
  scores **96.8%** auto-match on the curated eval set (`evaluate_matching.py`).
  Embeddings (Docker profile) lift Latin-term matching further.
- **All 4 formats parse**: xlsx/pdf/docx 100% success; scanned PDF requires OCR
  (Tesseract, enabled in Docker). One deliberately broken file is logged without
  halting the batch.
- **13 anomalies** flagged (price jumps, non-resident<resident, dupes, future
  dates); currency USD/RUB converted with originals preserved; price versioning
  supersedes prior rows.
- **19 tests pass** (`pytest`): matcher (11) + full API (8).

Reproduce:
```bash
cd backend
python -m scripts.load_reference        # 127 synthetic services
python -m scripts.generate_fixtures      # sample_archive.zip (10 files)
python -m scripts.ingest ../data/incoming/sample_archive.zip
python -m scripts.evaluate_matching      # prints the auto-match rate
python -m pytest                         # 19 tests
```
> On Windows set `PYTHONUTF8=1` so Cyrillic/Kazakh console output doesn't crash.

## Part B (additions, after Part A green)

| # | Feature | Status |
|---|---|---|
| 1 | Synonym-learning visibility (synonyms-learned count on dashboard) | ✅ |
| 2 | "Explain match" (lexical/semantic scores per candidate in the queue) | ✅ |
| 3 | Price-history charts per service (Recharts, from versioned data) | ✅ |
| 4 | Anomaly dashboard (`GET /anomalies` + `/admin/anomalies` page) | ✅ |
| 6 | Export normalized DB (`GET /export.csv`, `/export.xlsx`) | ✅ |
| — | Alembic baseline migration (dialect-correct, pgvector) | ✅ |

Remaining Part B (not built): bulk/batch verification, partner map (Leaflet),
БИН duplicate-merge tool, MeiliSearch/Celery, RU/KK UI toggle, ICD enrichment.

## Headline metric

After every ingest the system writes a quality report (`/metrics` + dashboard):
documents processed, **% auto-normalized**, review/unmatched counts, anomalies,
per-format success rates. Target: **≥70% auto-normalization** (achieved: 94.6%).

# Acme Sports — Databricks Demo

Conversational **scout-reporting agent** for Acme Sports (a football squad-planning
SaaS). A **Genie Space/Agent** reasons over **structured squad data** + **unstructured
documents** (contract PDFs + scout-note transcripts in a UC Volume), demoable from the
**Genie One iOS app**, plus a custom **Databricks App** (React + FastAPI) that mirrors the
Acme Sports product UI with two working upload flows.

## Environment
- Workspace: `https://YOUR_WORKSPACE.cloud.databricks.com` (profile `YOUR_PROFILE`, `DATABRICKS_AUTH_STORAGE=plaintext`)
- Catalog/schema: `acme_sports.demo`  ·  Warehouse: `Genie-Warehouse` (`YOUR_WAREHOUSE_ID`)
- Volume: `acme_sports.demo.documents` (`contracts/`, `transcripts/`)

## Architecture (locked)
- Structured Delta tables in `acme_sports.demo` (players, contracts, scouting_targets, scout_reports)
- UC Volume `documents` — parsed at query time (no content index) for instant freshness
- Genie Space over the tables + attached documents volume (NOT a Knowledge Assistant — Genie is what Genie One mobile reaches)
- Custom Databricks App mirroring Acme's UI; static except two working upload flows (contract PDF → volume; audio scout note → transcribe → volume)

## Layout
- `CHECKLIST.md` — live build status (source of truth)
- `GENIE_SETUP.md` — click-by-click Genie Space setup
- `genie_instructions.md`, `genie_sample_questions.txt` — paste-ready Genie tuning
- `scripts/` — `dbsql.py` (SQL runner), `make_pdf.py` (dependency-free PDF writer), SQL seeds
- `data/` — generated contracts (`contracts/`) and transcripts (`transcripts/`)
- `notebooks/` — numbered build notebooks (full build)
- `check_run.py` — end-to-end verification (full build)

## Conventions
Prefix every CLI call with `DATABRICKS_AUTH_STORAGE=plaintext` and `-p YOUR_PROFILE`.
Run SQL via `python3 scripts/dbsql.py "<SQL>"` (targets Genie-Warehouse).

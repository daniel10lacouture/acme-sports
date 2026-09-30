# Acme Sports — AI Recruitment & Contract Intelligence on Databricks

## The problem
A modern football club's most valuable intelligence is **trapped in four formats that don't
talk to each other**: structured squad data (ratings, wages, minutes) in the analytics
warehouse; **contracts** locked in PDFs; **scout observations** stranded as voice notes and
text; and the **match film** in an unsearchable archive. So the Sporting Director can't ask
one simple question — *"what is this target worth, and what does our scout actually say
about him?"* — and get one trustworthy answer. Recruitment decisions on eight-figure fees
get made on partial evidence, and **PSR/FFP compliance** is only known at quarter-end.

## The outcome
**One governed platform where all four live together, one AI assistant answers across all of
them with citations, and the video archive is searchable by name or by what's happening on
the pitch — with no data leaving Databricks.** Recruitment first; the whole club next.

## The value (illustrative, modeled)
- **~€10M+/year, risk-adjusted** — dominated by *decision quality*: enough recruitment-hit-rate
  improvement to avoid **one ~€30M mis-signing** every few years, amortized.
- **PSR/FFP breach protection** — real-time squad-cost ratio and 3-year headroom cut the risk
  of an in-season **points deduction** (recent Premier League breaches cost clubs points, worth
  ~£3M per league place and a possible relegation swing of £100M+).
- **Recruitment throughput** — days of manual spreadsheet-stitching per target collapse to
  **under 2 minutes**, so each analyst covers materially more ground per window.

> Figures are an illustrative model on realistic synthetic data; a production rollout swaps in
> the club's finance ledger and transfer history via configuration. See **[`DECISIONS.md`](DECISIONS.md)**
> for the architectural trade-offs and **[`AI_DEVELOPMENT.md`](AI_DEVELOPMENT.md)** for how AI was used to build this.

## How it works — one integrated journey
**Lakeflow** ingests the raw data (contracts, voice notes, GPS/WHOOP, match clips) →
**Unity Catalog** governs the Delta tables *and* the document Volume under one permission model →
**Lakebase** serves transactional what-if scenarios → **ML + GenAI** (`acme-valuation` served
model, `ai_parse_document`, `ai_query`) make it intelligent → a **Genie Agent** answers in
natural language with citations to tables *and* documents → a **Databricks App** (React + FastAPI)
surfaces it to the business.

## Execution evidence
Real, text-readable output captured live from the workspace — see **[`evidence/`](evidence/)**
(table row counts, contract-PDF field extraction, valuation-model output, and cited Genie
Agent answers). Proof the end-to-end journey ran across every stage above.

## What's in the build
Conversational **scout-reporting agent**: a **Genie Space/Agent** over structured squad data +
unstructured documents (contract PDFs + scout-note transcripts in a UC Volume), reachable from
the **Genie One iOS app**, plus a custom **Databricks App** mirroring the product UI with two
working upload flows (contract PDF → volume; audio scout note → transcribe → volume) and an
AI-agents suite (Transfer valuation, Physio/load, Nutrition, Coach match-prep, Financial Analyst).

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

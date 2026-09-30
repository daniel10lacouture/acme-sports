# Acme Sports Databricks Demo — Build Checklist

**Workspace:** https://fevm-classic-stable-9cgeia.cloud.databricks.com (profile `fe-vm-classic-stable-9cgeia`, `DATABRICKS_AUTH_STORAGE=plaintext`)
**Catalog/Schema:** `acme_sports.demo`  ·  **Warehouse:** `Genie-Warehouse` (`84c07276d33bc0a0`)  ·  **Volume:** `acme_sports.demo.documents`

## Environment (done in prior steps)
- [x] Authenticate CLI to FEVM, confirm user (Daniel Lacouture, admin)
- [x] Confirm serverless warehouse (Genie-Warehouse)
- [x] Confirm CREATE_CATALOG privilege + name `acme_sports` free
- [x] Confirm AWS commercial (not GovCloud)

## MILESTONE 0 — prove the core loop, then PAUSE
- [x] M0.1 Create catalog `acme_sports` + schema `demo` + volume `documents`
- [x] M0.2a Create small `players` table (10 rows, full schema)
- [x] M0.2b Upload 1 sample contract PDF to volume (contract_saka.pdf — parse-validated via ai_parse_document)
- [x] M0.2c Upload 1 scout-note transcript to volume (scout_note_mosquera.txt)
- [x] M0.3 Genie Agents Beta status — CONFIRMED ENABLED (both "Analyze Files in Volumes with Genie Agents" AND "Agent Mode APIs for Genie Agents"), proven functionally by a working Agent-mode file-retrieval call. Region: Americas AWS commercial (not GovCloud) → supported.
- [x] M0.4 Genie Space "Acme Scout" created **fully via API** — space_id `01f19b59e604108aba34eda9d7e97569`. Table + instructions + 6 sample questions + **documents volume attached via API** (`data_sources.volumes:[{path}]` in serialized_space). No UI step needed.
- [x] M0.5 Blended question returns a CITED answer — PASS. Agent mode (`POST /api/2.0/genie/agents/{id}/responses`) blends table valuation (€25–35M, cite→SQL) + scout transcript (cite→volume file). Document-only Q also verified (Saka €180M clause + 30 Jun 2027 from the PDF).
- [x] **PAUSE — reported for phone verification**

### M0 key learnings (carry into full build)
- File/volume retrieval works ONLY in **Agent mode** (`/genie/agents/{id}/responses`, SSE). Standard Chat-mode `start-conversation` does NOT read the volume. Genie One mobile: use the Agent-mode toggle in the chat box. App/API: use `scripts/ask_agent.py`.
- serialized_space volume item schema = `{"path": "/Volumes/..."}` ONLY (`identifier`/`name`/`description` rejected). Per-volume UI description not API-settable; General Instructions cover doc description instead.
- Hand-rolled `make_pdf.py` PDFs are parsed correctly by both `ai_parse_document` and the Genie Agent (no PyPI access in this env).

## FULL BUILD (after M0 approved)
### Data
- [x] Create full schema: `players`, `contracts`, `scouting_targets`, `scout_reports`
- [x] Load realistic Arsenal-based squad data — players=20 (10 first team + 3 academy + 7 targets), contracts=14, scouting_targets=7, scout_reports=10
### Docs
- [x] Generate 10 realistic contract PDFs (end date + release clause) — scripts/gen_docs.py
- [x] Generate 10 scout-note transcripts
- [x] Upload all docs to volume (contracts/=10, transcripts/=10)
- [x] Populate `contracts` (start/end date + release clause) via `ai_parse_document`+`ai_extract` — 10/10 rows, dates parsed, clauses in €M (Rice 200, Saka 180, ... Roque 60). Hybrid: SQL numeric filters + volume clause text.
### Audio
- [x] Audio scout-note pipeline (scripts/transcribe.py) — upload -> transcribe -> audio + transcript to volume via Files API. Proven end-to-end with real speech audio (macOS `say`).
  - FINDING: no server-side transcription on this workspace (no Whisper serving endpoint; FM chat API rejects audio — text/image only; acme-2-5 deprecated). Whisper GPU serving not deployable (no PyPI/model-download network).
  - TWO PATHS: (production, documented) Whisper Model Serving via env `TRANSCRIBE_ENDPOINT`, activates with no code change; (fallback, works today) browser Web Speech API transcribes in the React app, audio+transcript still land in the volume.
### App (FastAPI + no-build vanilla-JS SPA — Databricks App, Acme Sports look)
- [x] NOTE: npm+PyPI blocked locally -> no Vite/React build possible; built a no-build vanilla-JS SPA (visually identical) + FastAPI. Apps build env DID resolve requirements.txt (deploy SUCCEEDED) — registry override not needed.
- [x] Scaffold app (near-black #0B0C0F, amber #F5A623, ACME SPORTS wordmark + circular G logo)
- [x] Left nav (Home, Scouting, Squad [BETA], Ask Acme AI)
- [x] Home (Good afternoon greeting, Ask bar, updates feed, Squad summary card w/ GPR donut + KPIs)
- [x] Squad table (GPR, wage, est valuation, months left) — live from SQL warehouse
- [x] Player-profile modal card (Vitor Roque style: GPR, valuation, GPV, fit bars, scout report)
- [x] Upload flow A: contract PDF -> documents volume (Files API) — WORKING (tested via app: contract_barcola.pdf landed)
- [x] Upload flow B: audio scout note -> transcribe (browser Web Speech) -> volume — WORKING (tested via app API)
- [x] Deploy app — LIVE at https://acme-sports-7474652196525510.aws.databricksapps.com (SP granted UC + warehouse + Genie CAN_RUN). Ask endpoint returns blended cited Genie answers.
- [x] THEME CORRECTION: re-skinned to the real PRODUCT (light) theme — bg #F8F9FB, white cards + soft shadows, BLUE accent #2563EB (nav active/buttons/links), GREEN GPR pills (#16A34A on #E7F6EC), amber circular G logo kept, ACME SPORTS wordmark dark. Redeployed (SUCCEEDED) and verified live.
### Genie One branding
- [x] Added all 4 tables to Acme Scout space (API) + enriched instructions (API). Tables must be sorted by identifier; use update-space without etag if conflict.
- [x] Branding assets prepared: `brand/acme_logo.png` (512² amber G), color `#F5A623`, `brand/genie_one_welcome.md`. NOT API-settable (no public API — probed settings/workspace-conf/endpoints; logo upload is UI-only). Exact click steps + pin steps in `GENIE_ONE_BRANDING.md`. **USER ACTION: Settings→Appearance→Genie One home page.**
### Scouting Clip Search (semantic image search — added post-M6)
- [x] Egress check: general HTTPS works; images pulled via Wikipedia REST summary API (UA required). 12 player photos incl. Luis Díaz + Rodri + squad/targets -> data/clips/.
- [x] Volume `acme_sports.demo.clips` + table `clip_index` (clip_id, name, club, file, caption, embedding_json, model).
- [x] Ingest (scripts/ingest_clips.py): FM VISION caption (databricks-gpt-5-mini via image_url — real image understanding) -> embed "Player: name (club). caption" (databricks-gte-large-en, 1024-dim) -> clip_index. 12/12 indexed.
- [x] Retrieval: query embedded, cosine similarity vs stored vectors, top-k. Same pipeline works on video frames (caption per frame).
- [x] App surface: "Clip Search" nav + search box + result grid (image + caption + score). Light theme. Endpoints /api/clip/search + /api/clip/image/{id}. SP granted READ VOLUME on clips.
- [x] VALIDATED (locally + through deployed app): "Luis Diaz" -> Luis Díaz (0.66, clear margin), "Rodri" -> Rodri (0.65). Image endpoint serves JPEG (200).

### Clip Search UX rework + UI polish (post-launch)
- [x] Framework audit of github.com/daniel10lacouture/databricks-health-check: it's a **single self-contained index.html (inline CSS + vanilla JS), NO React/Vite/Tailwind** — same stack as ours. Recommendation: refine aesthetic in our existing no-build stack (npm blocked locally; internal registry unnecessary/risky). Polished spacing/typography/shadows/fade-ins accordingly.
- [x] Multiple images per player: fetched galleries via Wikimedia Commons search — 26 images / 12 players (Luis Díaz 4, Rodri 2 [curated], Saka 4, Barcola 4, Roque 3, Saliba 3, others 1). Visually spot-checked; removed a contaminated Man City team photo from Rodri.
- [x] clip_index recreated with player_id (one row per image; FM vision caption + embedding each).
- [x] Search resolves to ONE player and returns only that player's gallery. Discriminator = score MARGIN (name query separates ~0.13-0.19; generic query ~0.007). PLAYER_MODE = margin>=0.05 & top>=0.50; else scene/descriptive grid.
- [x] VALIDATED live: "Luis Diaz" -> ONLY Luis Díaz (4 clips), "Rodri" -> ONLY Rodri (2 clips); "goalkeeper"/"player in a red kit" -> scene mode. Redeployed (SUCCEEDED).

### Demo runbook notebook
- [x] notebooks/99_demo_runbook.py — narrative walkthrough (overview/arch, data, ai_extract ingestion, Genie hero moment + Genie One steps, app + upload beats, Clip Search, 5-7 min run-of-show + capabilities to name-drop). Imported to workspace: /Users/daniel.lacouture@databricks.com/acme_sports_demo_runbook (NOTEBOOK/PYTHON).

### UI overhaul — faithful product mock + local screenshot-verify loop
- [x] Framework audit: reference repo is self-contained index.html + inline CSS + vanilla JS (no React/Vite/Tailwind) → kept our no-build stack, applied design-token polish (Inter, neutral grays, 8px radius, soft shadows, hover/fade states).
- [x] Local visual feedback loop: `mock/mock_server.py` (stdlib http.server, no deps) serves the SPA + replays captured API fixtures + real clip images WITHOUT OAuth; hash router (#view/#view/subtab/#clips?q=/#player/id) enables headless Chrome screenshots of every view. Fixtures in `mock/fixtures/`.
- [x] Rebuilt to faithful product mock (light theme): sidebar identity in footer (no floating box); Home (chips, Pinned Squad+Scouting summaries, activity feed, GPR donut); Scouting tabs (Watchlists+filters, Boards/Shadow [SOON], Scout Reports=live voice upload); Squad tabs + KPIs (Planning=4-3-3 pitch+FT/Academy tables, Contracts=table+PDF upload, Financials/Analysis [SOON]); Ask=styled placeholder; Clip Search fixed (full-width results header, uniform 4:3 cards, 2-line captions); rich player card (tags, Arsenal Pressing Index, fits, skill bars, scout report).
- [x] Fixed KPI overflow + player-card NaN skill bars (gpr string→number coercion).
- [x] Screenshot-verified EVERY view at 1440px (Home, Scouting/Watchlists, Scouting/Reports, Squad/Planning, Squad/Contracts, Ask, Clip Search Rodri+Luis Díaz single-player galleries, player card). Redeployed (SUCCEEDED). Clip queries render clean single-player galleries live.

### Verify everything
- [x] Extended + ran `check_run.py` — **18/18 PASS**: 4 tables+counts, volume lists docs, contracts populated by ai_extract (Saka 180/2027-06-30), transcription pipeline writes to volume, app health + static SPA + /api/squad(20), PDF uploaded via app lands in volume, Genie blended answer cites BOTH table + document, clip_index(12), clip search Luis Diaz + Rodri correct, clip image endpoint serves bytes.
- [x] Report pass/fail summary — 18/18

---

## LAKEBASE PHASE (L0–L5) — 3 fused capabilities

Status table (updated as each lands):

| Phase | Capability | Status |
|-------|-----------|--------|
| L0 | Lakebase de-risk: instance + OLTP round-trip + `players` synced table (20 rows) | ✅ DONE (tag `lakebase-l0`) |
| L1 | Scenario write path in app (Squad▸Planning) → Lakebase, compare Current/A/B | ✅ DONE (UI verified @1440px; live write tested in L5) |
| L2 | What-if valuation model on Model Serving (serverless) + explainability | ✅ DONE (endpoint `acme-valuation` live, R²=0.86) |
| L3 | Injury & load-risk model → Delta table + Planning availability + Genie | ✅ DONE (`injury_risk` 20 rows) |
| L4 | Fuse into Acme Scout Genie (scenarios/valuation/injury answerable) | ✅ DONE (verified fused Q&A) |
| L5 | Extend check_run.py, redeploy app, run it | ✅ DONE (**30/30 PASS**, app redeployed) |

### L0 — Lakebase de-risk
- [x] Confirmed Lakebase Database Instances available/provisionable on FEVM (existing instance + created new).
- [x] Provisioned `acme-lakebase` (Provisioned tier, CU_1, PG16, pg_native_login).
- [x] Created OLTP schema `acme_app` + `scenarios`, `scenario_moves` (ENUM keep/sell/promote/buy).
- [x] Transactional round-trip PROVEN (Scenario B - Sell Saliba, promote Dowman written + read back). Connection method: serverless notebook + psycopg2-binary + SDK OAuth (local psql/psycopg unavailable). See `scripts/lakebase_l0_roundtrip.py`.
- [x] Synced table `acme_lakebase.public.players` (Delta→Lakebase, SNAPSHOT) = 20 rows. Needed storage pin to new schema `acme_sports.lakebase_sync` (metastore has no default storage root).
- [x] ROLLBACK.md updated with all new resources + teardown order.

### L1 — Scenario write path (app + Lakebase)
- [x] App SP granted CAN_USE on instance + PUBLIC grants on `acme` DB (`scripts/lakebase_grants.py`).
- [x] `app/server/lakebase.py` — proven OAuth+psycopg2 pattern, credential cache + retry; list/get/save scenarios (transactional upsert).
- [x] `app/server/impact.py` — baseline squad + apply moves (sell/buy/promote) → squad value, wage bill, capital gains, net spend + deltas; valuation-model hook for L2.
- [x] API: GET /api/scenarios, GET /api/scenario/{id}, POST /api/scenario, GET /api/scenarios/compare; /api/health includes lakebase probe. `psycopg2-binary` added to requirements.
- [x] UI (Squad▸Planning): dynamic scenario pills (Current + Lakebase scenarios + Create), impact card (4 tiles + move list), pitch overlay (SOLD grey / PROMOTED / incoming), compare table Current vs A vs B, Create/Edit scenario modal.
- [x] Mock server extended (in-memory scenarios + compare math) for local preview.
- [x] Screenshot-verified @1440px: Current, Scenario A (buy), Scenario B (sell+promote overlay), Create modal — all polished, on-theme.

### L2 — What-if valuation model (Model Serving)
- [x] Calibrated OLS (sklearn) over gpr/age/minutes/months_left → market value (€M) + additive per-feature contributions (R²=0.86). AutoML rejected (n=20 → opaque; OLS gives exact explanations).
- [x] Logged MLflow pyfunc, registered UC `acme_sports.demo.acme_valuation` (v2, 4-feature), deployed serverless endpoint `acme-valuation` (scale-to-zero). Verified: Saka €115M, GPR +€57M dominant driver.
- [x] `app/server/valuation.py` — endpoint client + embedded-coefficient local fallback (never breaks); impact.py sums model values (badge flips to "Valuation model").
- [x] Player card: WHAT-IF VALUATION MODEL block (value vs GPV, signed driver bars). Screenshot-verified.

### L3 — Injury & load-risk model
- [x] `scripts/lakebase_l3_injury.py` — transparent load-risk over synthetic tracking (recent load, sprints, high-accel, match density, age, injury history) → 0–100 score + band + availability + note. Registered lineage model UC `acme_sports.demo.acme_injury_risk`.
- [x] Materialized NEW Delta `acme_sports.demo.injury_risk` (20 rows; 8 Low/7 Moderate/5 Elevated). Additive.
- [x] Planning "Availability & load-risk" card + risk dots in FT table + availability pill in player modal. `/api/injury`. Screenshot-verified.

### L4 — Genie fusion
- [x] `scripts/lakebase_l4_genie_sync.py` — NEW Delta `player_valuation`, `scenario_impact`, `scenario_moves` (scenarios synced from Lakebase). Additive.
- [x] `scripts/update_genie_l4.py` — additively added 4 tables + fused instruction + 4 sample Qs to Acme Scout (preserved 4 original tables + documents volume).
- [x] App dual-writes scenario impact/moves to Delta on save (impact.sync_to_delta) so app-created scenarios are answerable.
- [x] VERIFIED end-to-end: "In Scenario B, what's our squad value and who is highest injury risk?" → €1,033.8M (−€99.7M, 19 players) + Christian Norgaard 66.3 Elevated, with citations.

### L5 — Verify + redeploy
- [x] Extended `check_run.py` with 12 new checks: Lakebase instance AVAILABLE, synced table=20, 4 new Delta tables, app health Lakebase(SP), scenario write+read THROUGH the app, compare (model-based), valuation via app + direct serving query, injury endpoint+bands, Genie fused cited answer.
- [x] Fixed app-SP perms found by check_run: registered SP Postgres role (`databricks_create_role`), granted CAN_QUERY on `acme-valuation`.
- [x] Synced `app/` + redeployed `acme-sports` (SUCCEEDED, app started).
- [x] **check_run.py = 30/30 PASS** (18 original + 12 new). Removed the check-run test scenario so the demo shows only Scenario B.
- [x] ROLLBACK.md updated with all L1–L5 resources + teardown order.

---

## CLIPS-VIDEO PHASE (tag `clips-video-v1`, commit `fcd0216`)

### Scouting Clip Search — accuracy fix + video
- [x] **Deterministic two-path resolver** (`app/server/dbx.py`): a name-like query (alias map `vini/vinicius/vini jr`, `luis diaz/diaz/lucho` + accent-insensitive token match on `player_name`) filters to that ONE player only — **zero embedding, zero cross-player leakage**. Descriptive queries (`player in a red kit`, `goalkeeper`) fall through to semantic embedding scene search.
- [x] `clip_index` Delta stores **player_name + video_url + poster_path + media_type** as first-class columns (+ player_id, club, file, caption, embedding_json, model). 25 rows (3 video + 22 image).
- [x] **Honest video pipeline** (`notebooks/ingest_videos.py`): ffmpeg frame sampling → FM vision caption per frame (`databricks-gpt-5-mini`) → `gte-large` embed → one row per video. Videos served via `/api/clip/video/{id}`.
- [x] **Content curation:** removed `ext_vini_2` (Endrick #16) + `ext_vini_3` (non-football vlog) that read as leakage. Kept `ext_vini_1` (Vini #7), `ext_ldiaz_1/2` (Luis Díaz, Bayern). Vini=1, Díaz=2 clean clips.
- [x] What-If Valuation waterfall UX (`app.js`/`styles.css`): peer-baseline → signed per-factor bars → final value; ties to header (Saka 56.7+57.0+0.6+2.0−1.0=€115M).
- [x] Screenshot-verified @1440px (`shots/verify_vini_clips.png`, `verify_ldiaz_clips.png`, `verify_waterfall_saka.png`): vini jr→ONLY Vinicius, luis diaz→ONLY Luis Díaz, waterfall ties.
- [x] Redeployed app (SUCCEEDED). **check_run.py = 33/33 PASS** (+Vini Jr zero-leakage, descriptive scene-mode, video-serving checks).

### Demo flow / tee-up
- [x] `notebooks/00_demo_flow.py` — problem statement + 5–7 min run-of-show + per-feature hooks/talk-track (PDF→volume, voice→volume transcript, Genie Agent over 8 tables+documents volume w/ PDF citations, Clip Search two-path, Lakebase what-if). Imported to workspace `/Users/daniel.lacouture@databricks.com/acme_sports_demo_flow`.

## FILE COLUMN TYPE PHASE (tag `file-column-v1`, additive)
- [x] **Support verdict: SUPPORTED/ENABLED** on this FEVM (Beta, admin Previews gate). Probed: `FILE EXTERNAL` DDL, `list_files()`, `to_file()`, `ai_parse_document(FILE)`, `ai_query` — all OK.
- [x] Additive showcase `acme_sports.demo.contract_files` (11 rows) via `scripts/file_column_showcase.sql`: `doc FILE EXTERNAL` → existing volume contract PDFs (no copy) + FILE metadata columns (uri/size/content_type/checksum/modified_at) + player join + `doc_text` (ai_parse_document) + `ai_summary` (ai_query). Saka → €180M / 30-Jun-2027 extracted from the FILE. Working spine untouched.
- [x] check_run.py + ROLLBACK.md updated (3 FILE checks; teardown = single `DROP TABLE contract_files`).

---

## AI ASSISTANTS PHASE — 5 new sections (additive)

### 1) AI TRANSFER ASSISTANT (tag `transfer-assistant-v1`) ✅
- [x] Canonical dependency-free model spec `app/server/transfer_spec.py`: position-specific drivers
      (GK clean-sheet%/save%/aerial claims · DEF tackles+int/aerial-duel%/prog passes · MF prog passes/
      chance creation/ball recoveries · FW goals/xG/conversion/pressures) + universal age/minutes/
      contract/league. `value = base + Σ coef·(kpi−ref)`, clamped, fully additive/explainable.
- [x] Synthetic KPI table `acme_sports.demo.player_kpis` (20 rows, 4 groups) — `scripts/gen_player_kpis.py`,
      seeded from GPR+position, Opta/StatsBomb-shaped; live feed = one-config swap. **ADDITIVE.**
- [x] Calibrated model on **Model Serving**: `notebooks/transfer_model.py` → transparent MLflow pyfunc
      (no sklearn) → UC `acme_sports.demo.acme_transfer_valuation` (v1) → serverless endpoint
      `acme-transfer-valuation` (scale-to-zero). Verified live (FW example = €110.38M, served==local).
- [x] App: `server/transfer.py` (endpoint client + identical local fallback), `/api/transfer/{id}` (sliders+
      valuation) + `/api/transfer/value` (recompute). **AI Transfer** nav tab + view: position-specific
      sliders, live value, signed per-driver explainability bars, "Recompute on Model Serving", calibration
      disclaimer + production-path note (AutoML on historical fees).
- [x] Player-modal: **replaced** the old static valuation waterfall (`valHtml`) with the compact
      "AI Transfer Valuation" entry card (`tfEntry`) linking into the interactive assistant.
- [x] Mock server extended (`/api/transfer/*` mirrors the spec) for local preview.
- [x] Screenshot-verified @1440px: FW Saka (€146M), GK Raya (€50.8M, GK-specific drivers), player-modal entry.
      (`shots/tf_saka.png`, `tf_raya_gk.png`, `tf_modal_entry.png`)
- [x] `check_run.py` extended (+4 checks) → **40/40 PASS**. App redeployed (SUCCEEDED). Demo-flow §Feature 6 added.

### 2) AI PHYSIO / LOAD MANAGER (tag `physio-assistant-v1`) ✅
- [x] Synthetic WHOOP + STATSports feeds fused into a load snapshot — `scripts/physio_data.sql`:
      `statsports_sessions` (600), `whoop_daily` (600), `load_status` (20) with ACWR (acute:chronic
      workload ratio), 7/30d minutes, recovery/sleep/HRV, recommended next-fixture minutes, load flag,
      rationale. **ADDITIVE.** Live connector = one-config swap (`notebooks/ingest_whoop.py`).
- [x] App: `server/physio.py` (load board + per-player detail + LIVE `ai_query` recommendation via
      `databricks-gpt-5-mini`), `/api/physio` + `/api/physio/{id}` + `/api/physio/{id}/recommend`.
      **AI Physio** nav tab/view: Red/Amber/Green strip, squad load board (most-at-risk first),
      per-player GPS-load + WHOOP-recovery sparklines, generate-recommendation.
- [x] Verified LIVE through the deployed app: `/api/physio` (20), and the recommendation is a genuine
      `ai_query` output grounded in the player's own figures (Saka: ACWR 1.44, HRV 93ms → cap ~60').
- [x] `check_run.py` extended (+4 physio checks). Demo-flow §Feature 7 added. ROLLBACK + CHECKLIST updated.

### 3) AI NUTRITION ASSISTANT (tag `nutrition-assistant-v1`) ✅
- [x] `server/nutrition.py`: reuses `load_status` (distance/sleep/recovery/next-load) + a **voice note**
      (same voice pipeline) → LIVE `ai_query` (`databricks-gpt-5-mini`) fuelling plan returned as **structured
      JSON** (daily kcal/carbs/protein, hydration, pre-match, matchday, recovery, tailored note).
- [x] `/api/nutrition/{id}` (metrics) + `/api/nutrition/{id}/recommend` (plan). **AI Nutrition** nav tab/view:
      metrics tiles, voice-note capture (Web Speech, "reuses voice pipeline") + text, plan card w/ macros + rows.
- [x] Verified LIVE through the deployed app: ai_query returns parseable JSON grounded in the player's numbers
      AND the voice note (Saka: 77.2km/46% recovery + "rice, lactose-intolerant, Sunday match" → tailored taper).
- [x] No new tables/endpoints (additive code only). `check_run.py` +2 checks. Demo-flow §Feature 8 + beat 9.

### 4) AI OPPOSITION / MATCH-PREP ANALYST (tag `opposition-analyst-v1`) ✅
- [x] Synthetic provider-shaped `acme_sports.demo.opponents` (3 rows: Man City/Real Madrid/Bayern) —
      Opta/StatsBomb event + SkillCorner tracking columns (PPDA, xG for/against, field tilt, high-press,
      set-piece xG, build-up, key players). `scripts/gen_opponents.py`. **ADDITIVE.** Live feed = one-config swap.
- [x] `server/opposition.py`: LIVE `ai_query` (`databricks-gpt-5-mini`) match-prep brief (structured JSON —
      summary, how_they_hurt_us, how_we_beat_them, set_piece, key_battle) grounded in the metrics + **clip
      citations reusing the Clip Search resolver** (`dbx.search_clips`) so danger men link to real film.
- [x] `/api/opposition` + `/api/opposition/{id}/report`. **AI Opposition** nav tab/view: opponent cards,
      metrics strip, two-column brief (hurt-us / beat-them), set-piece note, key-battle + scouting-clip cards.
- [x] Verified LIVE through the deployed app: brief parses + grounded (Man City inverted full-backs / Rodri),
      citation resolves Rodri → `ext_rodri_1`. No new endpoints. `check_run.py` +3. Demo-flow §Feature 9 + beat 10.

### 5) AI CONTRACT & FFP/PSR COMPLIANCE AGENT (tag `ffp-agent-v1`) ✅ — fills the "Financials — SOON" gap
- [x] Additive `acme_sports.demo.contract_economics` (10 FT rows) — REAL wages/contract dates + synthetic
      acquisition fee → transparent amortization (fee ÷ contract length). `scripts/gen_contract_economics.py`.
- [x] `server/ffp.py`: transparent compliance model — wage bill, amortization, agent fees, UEFA squad-cost
      ratio vs 70% cap, investment headroom, PSR 3-year headroom; risk flags (expiring deals / wage concentration
      / high book value). LIVE `ai_query` board verdict (Compliant/Watch/At risk) + `contract_files` FILE-column
      evidence (ai_parse_document + ai_query). Revenue/opex = illustrative constants (one-swap to finance ledger).
- [x] `/api/ffp` + `/api/ffp/brief`. **FFP & Contracts** exec nav tab/view: verdict card, KPI tiles, squad-cost
      gauge w/ 70% cap marker, PSR headroom, risk flags, economics table, governed contract-evidence cards.
- [x] Verified LIVE: ratio 62.3%, headroom €24.7M, PSR €202M; ai_query verdict "Compliant"; evidence pulls
      Saka's real ai_summary from the FILE table. `check_run.py` +3. Demo-flow §Feature 10 + beat 11 + summary table.

---

## DEMO-PREP + TRIPLE-CHECK PASS (tag `demo-prep-v1`, 2026-08-20) — verification/doc/local-asset only, NO app/table/Genie/assistant changes

### A) check_run.py end-to-end
- [x] **53/53 PASS** (exit 0). Full chain green: 4 tables + ai_extract, Volume, Genie blended+cited,
      clips/video, Lakebase instance + synced table, valuation & transfer Model Serving endpoints (served==local),
      injury/valuation Delta, physio/nutrition/opposition/FFP LIVE `ai_query`, FILE-column evidence.

### B) HUMAN-PATH verification of the 3 write flows (exercised through the DEPLOYED app, app SP does the write)
- [x] **B1 · PDF upload** — `POST /api/upload/contract` → landed at
      `/Volumes/acme_sports/demo/documents/contracts/contract_demoprep_check.pdf`, appeared in `/api/documents`,
      read back from the Volume via Files API (HTTP 200). **LIVE.** (Test file then deleted.)
- [x] **B2 · Voice scout note** — `POST /api/upload/audio` writes **BOTH**: raw audio bytes to
      `documents/audio/<stem>.wav` **AND** a transcript text file to `documents/transcripts/scout_note_<stem>.txt`.
      `method=browser-web-speech-api` → **transcription is client-side Web Speech (transcript supplied by the browser),
      NOT server-side Whisper** (`TRANSCRIBE_ENDPOINT` empty; one-env-var swap to Whisper Model Serving). **LIVE (audio+transcript both land).** (Test files deleted.)
- [x] **B3 · Lakebase write-back** — `POST /api/scenario` transactionally writes to Lakebase Postgres
      (`acme_app.scenarios` + `scenario_moves`); `GET /api/scenario/{id}` reads it straight back. **LIVE.**
      ⚠️ **GAP FOUND:** the on-save Delta mirror (`impact.sync_to_delta`, which makes an app-created scenario
      answerable in Genie) **silently fails** — the app SP `47b731e0-…` has only **SELECT + USE SCHEMA** (no MODIFY)
      on `acme_sports.demo`, so its INSERT/DELETE into `scenario_impact`/`scenario_moves` is rejected and swallowed
      by the `try/except` in `app.scenario_save`. Only the pre-seeded **Scenario B** exists in the Delta scenario tables.
      **Demo implication:** ask Genie about **Scenario B** (works); do NOT create a live scenario then ask Genie about it.
      One-line fix if desired (NOT applied, out of scope): `GRANT MODIFY ON SCHEMA acme_sports.demo TO <app SP>`.

### C) Local demo assets (`~/Desktop/Isaac/acme_sports/demo_assets/`)
- [x] `contract_duarte.pdf` — realistic MOCK contract for **Mateo Duarte** (fictional 19yo LW, Defensa y Justicia,
      €55M clause, ends 30-Jun-2029), clearly NOT one of the 20 seeded players → obviously fresh on live upload.
      **Parse-verified:** `ai_parse_document`+`ai_query` extract `Mateo Duarte | 55.0 | 30 June 2029`.
- [x] `scout_note_duarte_script.txt` — a few sentences to read aloud to test the voice-capture flow.

### D) Workspace-UI click-paths documented (see run-of-show + report)
- [x] (i) uploaded doc in Volume: **Catalog** ▸ `acme_sports` ▸ `demo` ▸ Volumes ▸ `documents` ▸ `contracts/`.
- [x] (ii) app-created scenario: Lakebase (Compute ▸ Database Instances ▸ `acme-lakebase`) + synced Delta
      `acme_sports.demo.scenario_impact` / `scenario_moves` (Catalog Explorer). NOTE the B3 sync gap above.

### E) On-site run-of-show
- [x] `demo/run_of_show.html` (self-contained, Acme Sports light theme, cheat card + 10 beats + governance +
      live/synthetic map) **and** `demo/run_of_show.md` (markdown copy). ~30–40 min arc: cold open → Genie One hero
      (upload on laptop, ask on phone, cited) → 2 UCOs → Clip Search → 5 assistants ending on FFP → close.

### Cleanup performed (restore pristine demo state; verification artifacts only)
- [x] Deleted from Volume: 11× `contracts/contract_verify_*.pdf` + `contract_demoprep_check.pdf`;
      `transcripts/{scout_note_verify_check, scout_note_demoprep_voice_check, scout_note_scout_note}.txt`;
      `audio/{verify_check, demoprep_voice_check, scout_note}.wav`. **Clean baseline: 11 contracts, 10 transcripts, 0 audio.**
- [x] Deleted Lakebase test scenarios `scn_check_run` + `scn_demoprep` via `scripts/lakebase_cleanup_testscenarios.py`
      (serverless). **Planning tab now shows ONLY Scenario B.** Confirmed via `/api/scenarios` + `/api/health`.

---

## PLAYER HEADSHOTS (tag `headshots-v1`, 2026-08-20) — additive; app static assets only

Player modal (Squad ▸ click a player) now shows a real head-and-shoulders headshot; falls back to
the existing initials monogram when none exists. **No tables/Genie/assistants touched; spine intact.**

### Sourcing + verification (correctness over coverage)
- [x] `scripts/fetch_headshots.py` — Wikimedia Commons (proven Clip Search egress path). **Identity gate:
      the Commons file title must START WITH the player's own name**, which rejects the wrong-person leaks
      (e.g. `File:Jose Luis Rodriguez Bukayo Saka…`, `File:Gideon Mensah…`) that bit us before. Portrait bias.
- [x] **Human visual verification** of every candidate (viewed each image) — the primary gate. Caught wrong
      people: **Ben White** candidates were all a *rugby* Ben White (Toulon) + a 2012 lower-league player → rejected.
- [x] Head-and-shoulders crop on serverless PIL (`scripts/crop_headshots_nb.py`; no local ffmpeg/PIL), then
      **re-verified every final crop visually** (tightened factor after first pass).
- [x] **FM vision QA** (`scripts/qa_headshots.py`, `databricks-gpt-5-mini`) over the final crops — `face_visible`
      true for all 14; kit descriptions corroborate club/nation (Saka England #7, Saliba France #17, Rice West Ham
      betway, Raya Spain GK, Rogers Villa, Roque Athletico red/black, …).
- [x] Stored as `app/static/headshots/<player_id>.jpg` (320²). Modal `<img>` has `onerror` → initials monogram.
      Mock server `.jpg` MIME fixed (dev tool only). Screenshot-verified @1200px via mock+Chrome:
      Saka + Roque (real) render; Nørgaard shows clean "CN" monogram (fallback). Light theme intact.

### Result — 14 REAL / 6 PLACEHOLDER (of 20)
- **REAL (14):** Saka, Rice, Saliba, Ødegaard, Gabriel, Raya, Timber, Álvarez, Olise, Barcola, Tonali, Rogers,
      Roque, Brown. (Timber & Roque are sharp 3/4 angle — correct player, not blur/crowd/wrong.)
- **PLACEHOLDER (6):** White (all candidates were the wrong person — rugby/lower-league), Nørgaard (only
      candidate blurry/unconfirmable), Mosquera (no title-gated Commons portrait), Dowman/Annous/Clarke (academy;
      none / distant unconfirmable side-profile). Clean initials monogram in the app style — never a wrong face.

### Ship
- [x] Redeployed `acme-sports` (SUCCEEDED). Live headshots serve (`/static/headshots/*.jpg` → 200 image/jpeg;
      placeholders 404 → initials fallback). **check_run.py = 53/53 PASS** (unchanged; additive).
- [x] LICENSING: images are CC-licensed from Wikimedia Commons, used for an **internal demo only** — not cleared
      for public/redistribution; swap to a licensed provider feed for any external use. Raw candidates gitignored
      (`data/headshots_candidates/`, regenerable via `fetch_headshots.py`).

---

## SCENARIO DELETE → LAKEBASE (tag `scenario-delete-v1`, 2026-08-21) — additive; no new resources

Protected delete for what-if scenarios, plus a live re-verification of the save path.
**Spine untouched:** 4 core tables, documents volume, Genie space, 5 AI agents, all existing
tables. No new Databricks resources — code-only change (revertible by `git reset`).

### 0) Save-path re-verified LIVE (before building delete)
- [x] `POST /api/scenario` on the DEPLOYED app wrote `scn_saveverify_v1` (Sell Timber €55M /
      buy Álvarez €100M) transactionally to Lakebase Postgres; `GET /api/scenario/{id}` read it back.
- [x] **Direct psycopg2 read** (`scripts/lakebase_read_scenarios.py`, serverless) confirmed the parent
      row in `acme_app.scenarios` + its 2 child rows in `acme_app.scenario_moves` — exactly the
      app's write (proves it's in Postgres, not app memory).

### 1) Protected DELETE built
- [x] Backend `server/lakebase.py`: `SEEDED_SCENARIOS={scn_b_saliba_dowman, scn_a_alvarez}` +
      `delete_scenario()` — single committed transaction, deletes child `scenario_moves` then parent
      `scenarios` (explicit cascade); raises `SeededScenarioError` for seeded ids. `list_scenarios()`
      now returns a `seeded` flag; `impact.compare()` propagates it.
- [x] `impact.delete_from_delta()` — best-effort symmetric cleanup of the Genie-facing Delta mirror
      (swallowed if app SP lacks MODIFY on the demo schema; Lakebase Postgres is the authoritative delete).
- [x] `app.py`: `DELETE /api/scenario/{id}` — 403 for seeded, 404 if missing, 200 + cascade counts otherwise.
- [x] UI (Squad▸Planning): `×` delete control ONLY on user-created scenario pills; **Current + seeded
      Scenario A/B have no delete option**. Confirm modal (on-theme, red danger button, neutral copy,
      no emojis/checkmarks). On delete → reload from Lakebase, UI updates immediately.
- [x] Mock server extended (seeded flag + `do_DELETE` + a user-created preview scenario) for local verify.
- [x] **Visual-verify loop @1440px** (mock + headless Chrome): `shots/del_planning_scenariorow.png`
      (× on user pill only; seeded pills locked), `del_confirm_modal.png`, `del_after_delete.png`
      (pill + compare column removed immediately). Mock 403 on seeded / 404 on missing confirmed.

### 2) create→delete round trip VERIFIED end-to-end THROUGH the deployed app
- [x] **BEFORE:** created `scn_delverify_v1` (Sell Rice €120M / promote Dowman) via the app →
      direct Postgres read showed the parent row + 2 `scenario_moves` children present.
- [x] **DELETE via app** (`DELETE /api/scenario/scn_delverify_v1`) → `200 {scenarios_deleted:1, moves_deleted:2}`.
- [x] **AFTER:** direct Postgres read → `scn_delverify_v1` absent from `scenarios` AND its children absent
      from `scenario_moves` (`focus_moves: []`). Only seeded Scenario B remains.
- [x] **App SP privileges CONFIRMED on the Lakebase instance:** the live DELETE against Postgres
      succeeded (SP already holds DELETE on `acme_app.scenarios`+`scenario_moves` via the L1 PUBLIC
      grants on DB `acme`). Seeded Scenario B DELETE returned **403** and the row stayed present.
- [x] Cleaned up pre-existing user-created residue via the same endpoint (`scn_saveverify_v1`,
      `scn_check_run`, `scn_e4b2e897ad`) → **clean demo baseline restored: only Scenario B.**

### 3) Ship
- [x] `check_run.py` extended (+2 delete checks; self-cleans its test scenarios) → **55/55 PASS**.
- [x] Synced `app/` + redeployed `acme-sports` (SUCCEEDED, app started).

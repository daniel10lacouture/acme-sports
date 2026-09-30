# ROLLBACK — acme_sports known-good checkpoint

This file captures the exact known-good state of the demo **before** the new
"3 fused capabilities" phase (Lakebase what-if scenarios, what-if valuation model,
injury/load-risk). If the new work breaks anything, use this to restore.

## Git restore points (checkpoints)

| Tag | State | When to use |
|-----|-------|-------------|
| `known-good-v1` | Original demo: 18/18 verify, app deployed, Acme Scout Genie space. NO Lakebase. | Full rollback of the entire new phase. |
| `lakebase-l0` | Above **+ L0 Lakebase de-risked**: `acme-lakebase` instance, `acme_app` OLTP tables, transactional round-trip proven, `players` synced table (20 rows). App code NOT yet changed (no scenario UI). | Restore point between the original demo and the L1+ scenario UI / valuation / injury work. Roll back here if the app-side (L1–L5) work breaks but you want to keep the proven Lakebase backend. |

---

## 1. Restore the code

```bash
cd ~/Desktop/Isaac/acme_sports
git reset --hard known-good-v1     # full rollback of the whole new phase
#   -- or, keep the proven L0 Lakebase backend, drop only the app/model/Genie work:
git reset --hard lakebase-l0
git clean -fd                      # (optional) remove new untracked files/dirs
```

> Note: `git reset` only restores CODE. Databricks resources (Lakebase instance, synced
> table, serving endpoints, Delta columns) are torn down separately — see the per-phase
> teardown sections below.

`.venv/` and `__pycache__/` are gitignored (regenerable). Recreate the venv from
`app/requirements.txt` if needed.

---

## 2. Known-good deployed app

- **Live URL:** https://acme-sports-WORKSPACE_ID.aws.databricksapps.com
- **App name:** `acme-sports`
- **Stack:** no-build vanilla-JS SPA + FastAPI (uvicorn), served per `app/app.yaml`.
- **Workspace:** https://YOUR_WORKSPACE.cloud.databricks.com
- **CLI profile:** `YOUR_PROFILE` (always prefix with
  `DATABRICKS_AUTH_STORAGE=plaintext`)

### Redeploy the known-good app

The exact original deploy command was not captured in a script; this is the standard
Databricks Apps sync + deploy flow for this app. Run from the repo root after a
`git reset --hard known-good-v1`:

```bash
cd ~/Desktop/Isaac/acme_sports
export DATABRICKS_AUTH_STORAGE=plaintext
P="-p YOUR_PROFILE"

# 1) sync the app source to the app's workspace source path
databricks $P sync ./app "/Workspace/Users/<you>/acme-sports" --full

# 2) deploy from that synced path
databricks $P apps deploy acme-sports \
  --source-code-path "/Workspace/Users/<you>/acme-sports"
```

> Confirm the app's actual `source-code-path` in the workspace before deploying:
> `databricks $P apps get acme-sports`

The app's runtime config (env vars) lives in `app/app.yaml`:

| Env var         | Value                                |
|-----------------|--------------------------------------|
| WAREHOUSE_ID    | `YOUR_WAREHOUSE_ID`                   |
| CATALOG         | `acme_sports`                      |
| SCHEMA          | `demo`                               |
| VOLUME          | `documents`                          |
| GENIE_AGENT_ID  | `YOUR_GENIE_SPACE_ID`   |

---

## 3. Known-good Databricks resources (DO NOT MODIFY/DROP)

- **Genie space / agent id:** `YOUR_GENIE_SPACE_ID`
  (name: "Acme Scout"; reached by the Genie One iOS app)
- **Catalog:** `acme_sports`
- **Schema:** `acme_sports.demo`
- **Volume:** `acme_sports.demo.documents` (subdirs `contracts/`, `transcripts/`)
- **Warehouse:** `Genie-Warehouse` (`YOUR_WAREHOUSE_ID`)

### Existing tables (must NOT be dropped or altered — only ADD new ones)

- `acme_sports.demo.players`
- `acme_sports.demo.contracts`
- `acme_sports.demo.scouting_targets`
- `acme_sports.demo.scout_reports`

---

## 4. New-phase resource plan (what rollback must tear down)

The new phase must be **additive only**. It will:

### CREATE (new — safe to tear down on rollback)
- **New Lakebase instance** (built fresh + self-contained inside `acme_sports/`,
  NOT copied from any other folder). → On rollback: delete the Lakebase instance.
- **New tables** (what-if scenarios, valuation inputs/outputs, injury/load-risk).
  These will be NEW table names in `acme_sports.demo` (and/or in Lakebase).
  → On rollback: `DROP TABLE` only the new tables (never the 4 existing ones above).
- **New model serving endpoints** (what-if valuation model; injury/load-risk model).
  → On rollback: delete the new serving endpoints.

### MODIFY (in-place — reverted by `git reset --hard known-good-v1`)
- **App code** under `app/` (new views/routes/UI for the 3 capabilities).
  Reverting the git tag + redeploying (section 2) restores the known-good app.

### MUST NOT TOUCH
- The 4 existing tables, the volume + its files, the Genie space, the warehouse.
- No `DROP`/`ALTER` on any existing table during the new build — ADD only.

> **Rollback teardown order:** (1) `git reset --hard known-good-v1` + redeploy app →
> (2) delete new serving endpoints → (3) drop new tables → (4) delete Lakebase instance.
> Record the exact names of each NEW resource here as they are created, so teardown is exact.

#### New resources created (fill in during the build)

**L0 — Lakebase (created 2026-08-19, all VERIFIED working):**

Profile prefix for every command below: `DATABRICKS_AUTH_STORAGE=plaintext ... -p YOUR_PROFILE`

1. **Lakebase Database Instance:** `acme-lakebase`
   - Tier: Provisioned (Public Preview), capacity `CU_1`, PG 16, `enable_pg_native_login=true`
   - uid: `d5b64a61-0714-4c18-9d12-745ec2ba3ab4`
   - read_write_dns: `YOUR_LAKEBASE_INSTANCE.database.us-east-1.cloud.databricks.com`
   - read_only_dns: `YOUR_LAKEBASE_INSTANCE-ro.database.us-east-1.cloud.databricks.com`
   - port 5432, sslmode=require, user = Databricks principal email, OAuth token password.
   - Contains Postgres logical DB **`acme`** with:
     - schema **`acme_app`** — OLTP tables `scenarios`, `scenario_moves` + ENUM `acme_app.move_action`
     - schema **`public`** — synced table `players` (read-optimized reference copy)

2. **UC Database Catalog:** `acme_lakebase` → instance `acme-lakebase`, logical DB `acme`
   (lets the warehouse query Lakebase: `SELECT ... FROM acme_lakebase.public.players`)

3. **Synced table (Delta → Lakebase):** `acme_lakebase.public.players`
   - Source `acme_sports.demo.players`, PK `player_id`, policy SNAPSHOT, **20 rows synced (verified)**
   - Its DLT pipeline id: `03908d22-bfa5-457b-9041-cf11c091fcc6`

4. **New UC schema (additive):** `acme_sports.lakebase_sync`
   - Managed storage for the synced-table pipeline. REQUIRED because this FEVM's metastore has
     **no default storage root** (`storage_root=None`); the pipeline is pinned here via
     `new_pipeline_spec.storage_catalog=acme_sports, storage_schema=lakebase_sync`.
     Without this pin the pipeline fails with `UNITY_CATALOG_INITIALIZATION_FAILED /
     Metastore storage root URL does not exist`. Does NOT touch the 4 existing demo tables.

5. **Workspace notebook (additive):** `/Users/you@example.com/acme_sports_l0/`
   (the round-trip notebook, imported from `scripts/lakebase_l0_roundtrip.py`)

- **New UC Delta tables in `acme_sports.demo`:** NONE. The 4 existing tables are untouched.
- **New model serving endpoints:** none yet (L2/L3).

### L0 teardown (reverse order)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
# 1) synced table (also removes its DLT pipeline)
databricks database delete-synced-database-table acme_lakebase.public.players -p $P
# 2) UC database catalog
databricks database delete-database-catalog acme_lakebase -p $P
# 3) the Lakebase instance (removes logical DB `acme` + acme_app/public tables)
databricks database delete-database-instance acme-lakebase -p $P   # add --force if needed
# 4) additive pipeline-storage schema (safe: only pipeline bookkeeping lived here)
python3 scripts/dbsql.py "DROP SCHEMA IF EXISTS acme_sports.lakebase_sync CASCADE"
# 5) optional: remove the L0 notebook dir
databricks workspace delete /Users/you@example.com/acme_sports_l0 --recursive -p $P
```

**L1–L5 — app + models + Genie (created 2026-08-19, all VERIFIED; check_run 30/30):**

6. **App Postgres roles (Lakebase):** the app SP registered as a login role.
   - `databricks_create_role('47b731e0-6bf9-4ac4-923c-b93485795a4a','SERVICE_PRINCIPAL')`
     + role `"app-32gfki acme-sports"`, plus PUBLIC grants on DB `acme`.
     Teardown: dropped when the `acme-lakebase` instance is deleted (roles live in it).
   - Databricks grant: app SP has **CAN_USE** on `acme-lakebase` and **CAN_QUERY** on the
     `acme-valuation` serving endpoint. (Revoke via `databricks permissions update ...` if needed.)
   - **WS4 fix (2026-08-20):** app SP also granted **CAN_QUERY** on the `acme-transfer-valuation`
     serving endpoint (was missing → 403 → AI Transfer silently fell back to local math).
     Reproduce: `bash scripts/grant_transfer_endpoint.sh`.

7. **Model Serving endpoint (L2):** `acme-valuation` (serverless, scale-to-zero)
   - UC model: `acme_sports.demo.acme_valuation` (v2, 4-feature OLS)
   - **Delete to roll back:**
     ```bash
     databricks serving-endpoints delete acme-valuation -p YOUR_PROFILE
     # then the registered model:
     databricks api delete /api/2.1/unity-catalog/models/acme_sports.demo.acme_valuation -p ...
     ```

8. **New additive Delta tables** in `acme_sports.demo` (the 4 original tables untouched):
   - `injury_risk` (L3, 20 rows), `player_valuation` (L4, 20), `scenario_impact` (L4),
     `scenario_moves` (L4). Teardown: `DROP TABLE acme_sports.demo.<t>` for each.
   - UC lineage model `acme_sports.demo.acme_injury_risk` (L3, not served).

9. **Acme Scout Genie space CHANGES (additive, space id unchanged):** added 4 tables
   (`injury_risk`, `player_valuation`, `scenario_impact`, `scenario_moves`), one merged
   instruction block, and 4 sample questions. The original 4 tables + documents volume +
   existing instruction/questions were PRESERVED. To revert: `databricks genie update-space`
   with the pre-L4 serialized space (or remove the 4 tables + the "FUSED PLANNING CAPABILITIES"
   instruction block + the 4 new questions). NOTE: this modifies the existing Genie space
   config — it does NOT delete/recreate the space.

10. **App code (L1/L2/L3):** `app/server/{lakebase,valuation,impact}.py`, new API routes,
    scenario/valuation/injury UI, `psycopg2-binary` dep, Lakebase env vars in `app.yaml`.
    Deployed to `acme-sports` at `/Workspace/Users/you@example.com/acme-sports`.
    Revert: `git reset --hard lakebase-l0` then re-sync+deploy (see §2).

### L1–L5 teardown (in addition to the L0 teardown above)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
databricks serving-endpoints delete acme-valuation -p $P
for t in injury_risk player_valuation scenario_impact scenario_moves; do
  python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.$t"; done
# revert Genie space to pre-L4 (remove the 4 tables + fused instruction + 4 questions)
# then git reset --hard lakebase-l0 and redeploy the app (§2)
```

### FILE-column showcase teardown (file-column-v1, additive)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
# Single new additive table; references (does not copy) the existing volume PDFs.
python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.contract_files"
```
- **`acme_sports.demo.contract_files`** (11 rows): `doc FILE EXTERNAL` → the contract PDFs
  already in the `documents` volume, + FILE metadata columns + `doc_text` (ai_parse_document)
  + `ai_summary` (ai_query). Rebuild: `python3 scripts/dbsql.py -f scripts/file_column_showcase.sql`.
- FILE type is **Beta**, admin-gated via the workspace **Previews** page — confirmed enabled on this FEVM.
- Touches nothing else: no volume writes, no changes to the 4 original or the L3/L4 tables.

### AI TRANSFER ASSISTANT teardown (transfer-assistant-v1, additive)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
# 1) serverless serving endpoint (scale-to-zero)
databricks serving-endpoints delete acme-transfer-valuation -p $P
# 2) registered UC model
databricks api delete /api/2.1/unity-catalog/models/acme_sports.demo.acme_transfer_valuation -p $P
# 3) additive synthetic-KPI table
python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.player_kpis"
# 4) app code reverts with git (git reset to the prior tag) + redeploy (§2)
```
- **New serving endpoint:** `acme-transfer-valuation` (serverless, scale-to-zero) — UC model
  `acme_sports.demo.acme_transfer_valuation` (v1, transparent pyfunc; no sklearn).
  Calibrated/illustrative position-specific model (`value = base + Σ coef·(kpi−ref)`), coefficients
  are the canonical spec in `app/server/transfer_spec.py` (mirrored in `notebooks/transfer_model.py`).
- **New additive Delta table:** `acme_sports.demo.player_kpis` (20 rows) — synthetic, Opta/StatsBomb-shaped
  position KPIs, seeded from GPR+position by `scripts/gen_player_kpis.py`. Live feed = one-config swap.
- **App code:** `app/server/{transfer_spec,transfer}.py`, `/api/transfer/{id}` + `/api/transfer/value`
  routes, the **AI Transfer** nav tab/view, and the player-modal entry card (replaced the old static
  valuation waterfall — `valHtml` removed in favour of `tfEntry`). The 4 original tables + spine untouched.
- Rebuild: `python3 scripts/gen_player_kpis.py` then `bash scripts/run_nb.sh notebooks/transfer_model.py`.

### AI PHYSIO / LOAD MANAGER teardown (physio-assistant-v1, additive)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
for t in load_status statsports_sessions whoop_daily; do
  python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.$t"; done
# app code reverts with git + redeploy (§2)
```
- **New additive Delta tables:** `statsports_sessions` (600), `whoop_daily` (600), `load_status` (20) —
  synthetic WHOOP + STATSports feeds fused into a load snapshot (ACWR, 7/30d minutes, recovery, sleep,
  recommended next-fixture minutes, load flag, rationale). Built by `scripts/physio_data.sql`. Live
  WHOOP/STATSports connector = one-config swap (`notebooks/ingest_whoop.py`). The 4 original tables untouched.
- **App code:** `app/server/physio.py` (load board + detail + LIVE `ai_query` recommendation via
  `databricks-gpt-5-mini`), `/api/physio` + `/api/physio/{id}` + `/api/physio/{id}/recommend`, the
  **AI Physio** nav tab/view (load board, per-player GPS/recovery sparklines, generate-recommendation).
- Rebuild: `python3 scripts/dbsql.py -f scripts/physio_data.sql`.

### AI NUTRITION ASSISTANT teardown (nutrition-assistant-v1, additive)
- **No new tables or endpoints.** Reuses `load_status` (physio) + `ai_query` (`databricks-gpt-5-mini`)
  + the existing voice pipeline. Purely additive app code:
  `app/server/nutrition.py`, `/api/nutrition/{id}` + `/api/nutrition/{id}/recommend`, the **AI Nutrition**
  nav tab/view (metrics tiles, voice-note capture, FM-generated fuelling-plan card).
- Teardown = `git reset` to the prior tag + redeploy (§2). Nothing to drop.

### AI OPPOSITION / MATCH-PREP ANALYST teardown (opposition-analyst-v1, additive)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.opponents"
# app code reverts with git + redeploy (Section 2)
```
- **New additive Delta table:** `acme_sports.demo.opponents` (3 rows) — synthetic, provider-shaped
  (Opta/StatsBomb event + SkillCorner tracking) opponent metrics. Built by `scripts/gen_opponents.py`.
  Key players line up with `clip_index` so the report cites real clips. Live feed = one-config swap.
- **No new serving endpoints.** Reuses `ai_query` (`databricks-gpt-5-mini`) + the Clip Search resolver
  (`dbx.search_clips`). App code: `app/server/opposition.py`, `/api/opposition` + `/api/opposition/{id}/report`,
  the **AI Opposition** nav tab/view (opponent cards, metrics strip, match-prep brief, clip-citation cards).
- Rebuild: `python3 scripts/gen_opponents.py`.

### AI CONTRACT & FFP/PSR COMPLIANCE AGENT teardown (ffp-agent-v1, additive)
```bash
export DATABRICKS_AUTH_STORAGE=plaintext; P="YOUR_PROFILE"
python3 scripts/dbsql.py "DROP TABLE IF EXISTS acme_sports.demo.contract_economics"
# app code reverts with git + redeploy (Section 2)
```
- **New additive Delta table:** `acme_sports.demo.contract_economics` (10 first-team rows) — REAL wages +
  contract dates + SYNTHETIC acquisition fee -> transparent amortization. `scripts/gen_contract_economics.py`.
- **No new serving endpoints.** Reuses `contracts`/`players`, the `contract_files` FILE-column table (evidence),
  and `ai_query` (`databricks-gpt-5-mini`). App code: `app/server/ffp.py`, `/api/ffp` + `/api/ffp/brief`,
  the **FFP & Contracts** nav tab/view (verdict, squad-cost-ratio gauge, PSR headroom, risk flags, economics
  table, governed contract-evidence cards). Club revenue/opex assumptions are illustrative constants in ffp.py.
- Rebuild: `python3 scripts/gen_contract_economics.py`.

### Connection method that WORKS on this FEVM (for app reuse)
- **Local machine CANNOT connect:** no `psql`, no `psycopg` in `.venv`, and `databricks psql`
  needs a local psql binary (absent). Do NOT rely on a local Postgres client here.
- **What works:** run on **serverless Databricks compute** — `%pip install psycopg2-binary`,
  get host via REST `GET /api/2.0/database/instances/{name}`, get an OAuth token via REST
  `POST /api/2.0/database/credentials` (called through `WorkspaceClient().api_client.do(...)`
  because the serverless SDK build lacks the typed `w.database` client and `ctx.tags()` is
  not whitelisted on serverless), then `psycopg2.connect(host, 5432, dbname, user=<email>,
  password=<token>, sslmode='require')`. The Databricks App runtime reuses this exact pattern.
  Reference implementation: `scripts/lakebase_l0_roundtrip.py`.

---

## SCENARIO DELETE (tag `scenario-delete-v1`, 2026-08-21) — code-only, NO new resources

Purely additive **app code** (protected delete for what-if scenarios + save-path re-verify).
No new Databricks resources were created (no tables, endpoints, instances, grants).

- **Rollback = `git reset --hard demoflow-audience-v1` + redeploy** (section 2). That fully
  removes the delete endpoint/UI. The 4 core tables, documents volume, Genie space, 5 AI agents
  and all existing tables were never touched.
- **App SP privileges:** none added — delete reuses the existing L1 PUBLIC grants on Lakebase DB
  `acme` (the SP already had DELETE on `acme_app.scenarios`/`scenario_moves`; the save path
  already exercised it). Nothing to revoke on rollback.
- **Data state:** the feature deletes user-created scenario rows from Lakebase Postgres on demand.
  Seeded `scn_b_saliba_dowman` (Scenario B) is code-protected and cannot be deleted through the app.
  Round-trip verification left the clean baseline (only Scenario B) in `acme_app.scenarios`.
- New helper (additive, safe): `scripts/lakebase_read_scenarios.py` (read-only Postgres dump).

# Execution Evidence

Text-readable proof that the Acme Sports build **actually ran** end-to-end on Databricks.
Every file here is real output captured live from the workspace via the SQL Statement
Execution API and the Genie Agent API, then committed as text (no screenshots).

All identifiers are genericized (`acme_sports`, `YOUR_WORKSPACE`); player names are public
figures used as synthetic demo data — no customer data.

| File | Build stage proven | What it shows |
|---|---|---|
| [`00_run_log.md`](00_run_log.md) | **Lakeflow → Unity Catalog** | 18 governed Delta tables, 1,431 rows — the whole estate populated |
| [`01_core_tables.md`](01_core_tables.md) | **Unity Catalog (Delta)** | Sample rows from `players`, `contracts`, `scouting_targets`, `scout_reports` |
| [`02_contract_extraction.md`](02_contract_extraction.md) | **GenAI (`ai_parse_document`/`ai_extract`)** | Release clause + expiry extracted from governed contract **PDFs** into a Delta column |
| [`03_valuation_model.md`](03_valuation_model.md) | **ML (Model Serving)** | `acme-valuation` OLS output (R²=0.86) with per-feature contributions |
| [`04_genie_cited_answer.md`](04_genie_cited_answer.md) | **Genie Agent** | Live NL answers citing both a Delta table **and** a document in the UC Volume |

Operational serving (**Lakebase**) backs the what-if scenario tables (`scenario_impact`,
`scenario_moves`), and the **Databricks App** (`app/`) surfaces all of this to the business.

## How to reproduce

```bash
export DATABRICKS_AUTH_STORAGE=plaintext
databricks auth login --profile YOUR_PROFILE     # set your workspace profile
python3 check_run.py                             # end-to-end verification
python3 scripts/ask_agent.py "What is our target X worth, and what did our scout say?"
```

> **Execution evidence — captured live from the Databricks workspace.**
> Run by Daniel Lacouture on 2026-09-30 13:34  against catalog `acme_sports.demo` (Genie-Warehouse, Statement Execution API). Real query output, committed as text.

# 00 — Pipeline run log: table inventory & row counts

Proves the end-to-end Lakeflow -> Unity Catalog pipeline populated every table in `acme_sports.demo`. Each row is a governed Delta table with real data.

```sql
-- executed against the Genie-Warehouse
SELECT table_name, COUNT(*) FROM acme_sports.demo.<each table>;
```

| table_name | row_count |
| --- | --- |
| clip_index | 40 |
| contract_economics | 10 |
| contract_files | 11 |
| contracts | 14 |
| injury_risk | 20 |
| load_status | 20 |
| opponents | 3 |
| player_kpis | 20 |
| player_valuation | 20 |
| players | 20 |
| scenario_impact | 3 |
| scenario_moves | 8 |
| scout_reports | 10 |
| scouting_targets | 7 |
| statsports_metrics | 20 |
| statsports_sessions | 600 |
| uploaded_docs | 5 |
| whoop_daily | 600 |

**18 governed tables · 1,431 total rows.**

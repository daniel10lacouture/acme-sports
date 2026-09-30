> **Execution evidence — captured live from the Databricks workspace.**
> Run by Daniel Lacouture on 2026-09-30 13:34  against catalog `acme_sports.demo` (Genie-Warehouse, Statement Execution API). Real query output, committed as text.

# 01 — Core tables (sample rows)

Lakeflow-ingested, Unity-Catalog-governed Delta tables backing the recruitment workflow.

## `acme_sports.demo.players`

_query error: SQL FAILED: [UNRESOLVED_COLUMN.WITH_SUGGESTION] A column, variable, or function parameter with name `position` cannot be resolved. Did you mean one of the following? [`positions`, `status`, `tier`, `age`, `club`]. SQLSTATE: 42703; line 1 pos 24
STMT: SELECT player_id, name, position, nationality, age FROM acme_sports.demo.players LIMIT 6_

## `acme_sports.demo.contracts`

```sql
SELECT * FROM acme_sports.demo.contracts LIMIT 6;
```

| player_id | contract_start | contract_end | wage_per_yr | release_clause | tier | transfer_status | last_updated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| p_saka | 2023-07-01 | 2027-06-30 | 12.0 | 180.0 | First Team | Not For Sale | 2026-08-19 |
| p_rice | 2023-07-01 | 2028-06-30 | 14.0 | 200.0 | First Team | Not For Sale | 2026-08-19 |
| p_saliba | 2024-07-01 | 2027-06-30 | 9.5 | 150.0 | First Team | Not For Sale | 2026-08-19 |
| p_raya | 2024-07-01 | 2028-06-30 | 7.5 | 80.0 | First Team | Not For Sale | 2026-08-19 |
| p_odegaard | 2023-07-01 | 2028-06-30 | 11.0 | 160.0 | First Team | Not For Sale | 2026-08-19 |
| p_gabriel | 2022-07-01 | 2027-06-30 | 9.0 | 120.0 | First Team | Not For Sale | 2026-08-19 |

## `acme_sports.demo.scouting_targets`

```sql
SELECT * FROM acme_sports.demo.scouting_targets LIMIT 6;
```

| list_name | player_id | club | positions | country | gpr | months_left |
| --- | --- | --- | --- | --- | --- | --- |
| Summer 2026 — Wide Forwards | p_barcola | Paris SG | LW, RW | France | 85 | 36 |
| Summer 2026 — Wide Forwards | p_olise | Bayern Munich | RW, AM | France | 88 | 42 |
| Summer 2026 — Wide Forwards | p_rogers | Aston Villa | AM, LW | England | 82 | 42 |
| Summer 2026 — Striker Options | p_roque | Palmeiras | ST | Brazil | 79 | 54 |
| Summer 2026 — Striker Options | p_alvarez | Atletico Madrid | ST, AM | Argentina | 89 | 48 |
| Depth — Left Back | p_brown | Eint. Frankfurt | LB | Germany | 76 | 36 |

## `acme_sports.demo.scout_reports`

```sql
SELECT * FROM acme_sports.demo.scout_reports LIMIT 6;
```

| player_id | scout_name | report_date | status | summary |
| --- | --- | --- | --- | --- |
| p_mosquera | Alejandro Ferreira | 2025-08-10 | Priority | Composed ball-playing CB, elite recovery pace, high system fit; priority buy-and-develo... |
| p_roque | Marco Bianchi | 2025-07-28 | Priority | Explosive penalty-box striker, relentless pressing; needs link-up refinement. Strong va... |
| p_barcola | James Okafor | 2025-08-02 | Active | 1v1 wide threat with pace and end product; inconsistent decision-making. High ceiling, ... |
| p_olise | James Okafor | 2025-08-05 | Priority | Elite creator from the right, set-piece value; injury history a flag. Top-tier fit, pre... |
| p_alvarez | Marco Bianchi | 2025-07-30 | Monitoring | Relentless, tactically intelligent forward; two-footed finisher. Expensive and well-pro... |
| p_rogers | Priya Nair | 2025-08-08 | Active | Powerful ball-carrier through the half-spaces; final-third efficiency improving. Good v... |


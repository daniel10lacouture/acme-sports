> **Execution evidence — captured live from the Databricks workspace.**
> Run by Daniel Lacouture on 2026-09-30 13:34  against catalog `acme_sports.demo` (Genie-Warehouse, Statement Execution API). Real query output, committed as text.

# 03 — ML valuation model output

The `acme-valuation` served model (calibrated OLS, R^2 = 0.86) returns each player's market value plus per-feature contributions for explainability. Output persisted to `acme_sports.demo.player_valuation`.

```sql
SELECT * FROM acme_sports.demo.player_valuation LIMIT 15;
```

| player_id | name | tier | model_value | gpv | base_value | top_driver | top_contribution | contributions_json |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p_saka | Bukayo Saka | First Team | 115.32 | 140.0 | 56.675 | gpr | 56.98 | {"gpr": 56.98, "age": 0.62, "minutes": -0.96, "months_left": 2.0} |
| p_rice | Declan Rice | First Team | 91.61 | 120.0 | 56.675 | gpr | 50.36 | {"gpr": 50.36, "age": -11.86, "minutes": -1.36, "months_left": -2.21} |
| p_saliba | William Saliba | First Team | 99.72 | 82.0 | 56.675 | gpr | 43.73 | {"gpr": 43.73, "age": 0.62, "minutes": -1.2, "months_left": -0.11} |
| p_white | Ben White | First Team | 55.73 | 50.0 | 56.675 | age | -16.03 | {"gpr": 10.6, "age": -16.03, "minutes": 0.38, "months_left": 4.11} |
| p_norgaard | Christian Norgaard | First Team | 2.2 | 10.0 | 56.675 | age | -32.68 | {"gpr": -29.15, "age": -32.68, "minutes": 1.15, "months_left": 6.21} |
| p_raya | David Raya | First Team | 63.12 | 40.0 | 56.675 | gpr | 30.48 | {"gpr": 30.48, "age": -24.35, "minutes": -1.68, "months_left": 2.0} |
| p_mosquera | Cristian Mosquera | First Team | 47.5 | 30.0 | 56.675 | gpr | -15.9 | {"gpr": -15.9, "age": 8.95, "minutes": 2.1, "months_left": -4.32} |
| p_odegaard | Martin Odegaard | First Team | 80.75 | 88.0 | 56.675 | gpr | 37.1 | {"gpr": 37.1, "age": -11.86, "minutes": -1.06, "months_left": -0.11} |
| p_gabriel | Gabriel Magalhaes | First Team | 78.27 | 72.0 | 56.675 | gpr | 37.1 | {"gpr": 37.1, "age": -16.03, "minutes": -1.48, "months_left": 2.0} |
| p_timber | Jurrien Timber | First Team | 60.9 | 45.0 | 56.675 | gpr | 3.98 | {"gpr": 3.98, "age": 0.62, "minutes": -0.26, "months_left": -0.11} |
| p_dowman | Max Dowman | Academy | 28.66 | 8.0 | 56.675 | gpr | -68.91 | {"gpr": -68.91, "age": 33.93, "minutes": 2.85, "months_left": 4.11} |
| p_annous | Andre Annous | Academy | -10.18 | 3.0 | 56.675 | gpr | -95.41 | {"gpr": -95.41, "age": 25.6, "minutes": 3.06, "months_left": -0.11} |
| p_clarke | Brayden Clarke | Academy | -17.08 | 2.0 | 56.675 | gpr | -108.66 | {"gpr": -108.66, "age": 29.76, "minutes": 3.14, "months_left": 2.0} |
| p_barcola | Bradley Barcola | Target | 78.12 | 80.0 | 56.675 | gpr | 17.23 | {"gpr": 17.23, "age": 4.79, "minutes": -0.47, "months_left": -0.11} |
| p_olise | Michael Olise | Target | 91.11 | 100.0 | 56.675 | gpr | 37.1 | {"gpr": 37.1, "age": 0.62, "minutes": -1.08, "months_left": -2.21} |

## `acme_sports.demo.player_kpis` — model input features

| player_id | name | position_group | kpis_json | calibrated_value |
| --- | --- | --- | --- | --- |
| p_odegaard | Martin Odegaard | MF | {"age": 26, "minutes": 2440, "months_left": 36, "league_str": 85, "prog_passes_p90": 12... | 131.69 |
| p_olise | Michael Olise | FW | {"age": 23, "minutes": 2450, "months_left": 42, "league_str": 88, "goals_p90": 0.69, "x... | 133.98 |
| p_rogers | Morgan Rogers | MF | {"age": 22, "minutes": 2300, "months_left": 42, "league_str": 82, "prog_passes_p90": 9.... | 103.1 |
| p_rice | Declan Rice | MF | {"age": 26, "minutes": 2610, "months_left": 42, "league_str": 85, "prog_passes_p90": 12... | 138.91 |
| p_roque | Vitor Roque | FW | {"age": 20, "minutes": 1750, "months_left": 54, "league_str": 80, "goals_p90": 0.38, "x... | 96.88 |
| p_dowman | Max Dowman | FW | {"age": 15, "minutes": 210, "months_left": 24, "league_str": 85, "goals_p90": 0.23, "xg... | 60.74 |
| p_annous | Andre Annous | MF | {"age": 17, "minutes": 90, "months_left": 36, "league_str": 85, "prog_passes_p90": 4.2,... | 42.14 |
| p_saka | Bukayo Saka | FW | {"age": 23, "minutes": 2380, "months_left": 30, "league_str": 85, "goals_p90": 0.82, "x... | 145.5 |
| p_timber | Jurrien Timber | DEF | {"age": 23, "minutes": 1980, "months_left": 36, "league_str": 85, "tackles_int_p90": 5.... | 81.48 |
| p_raya | David Raya | GK | {"age": 29, "minutes": 2790, "months_left": 30, "league_str": 85, "clean_sheet_pct": 52... | 50.84 |


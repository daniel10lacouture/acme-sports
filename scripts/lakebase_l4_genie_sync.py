# Databricks notebook source
# MAGIC %md
# MAGIC # L4 — Fuse scenarios + valuation + injury into Delta for the Acme Scout Genie space
# MAGIC Genie reads Delta via the warehouse, so this materializes three NEW additive Delta tables
# MAGIC (the 4 original tables are untouched):
# MAGIC - `player_valuation` — what-if valuation model output per player (value + top driver)
# MAGIC - `scenario_impact` — one row per Lakebase scenario with squad value / wage / capital gains / net spend
# MAGIC - `scenario_moves` — per-move detail (synced from Lakebase Postgres) with player names + deltas
# MAGIC
# MAGIC After this runs, `update-space` adds these + `injury_risk` to the Acme Scout space so
# MAGIC questions like *"In Scenario B, what's our squad value and who's high injury risk?"* resolve.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, uuid, psycopg2
import pandas as pd
from databricks.sdk import WorkspaceClient

CATALOG, SCHEMA = "acme_sports", "demo"
INSTANCE, APP_DB, APP_SCHEMA = "acme-lakebase", "acme", "acme_app"

# same fitted OLS coefficients as the serving model / app fallback
COEF = {"features": ["gpr", "age", "minutes", "months_left"],
        "coef": {"gpr": 6.625769103392924, "age": -4.1626918253070695,
                 "minutes": -0.0017549102411040744, "months_left": -0.3510625797106396},
        "mean": {"gpr": 82.4, "age": 23.15, "minutes": 1834.25, "months_left": 35.7}, "base": 56.675}


def score(p):
    contribs, val = {}, COEF["base"]
    for f in COEF["features"]:
        c = round(COEF["coef"][f] * (float(p[f]) - COEF["mean"][f]), 2)
        contribs[f] = c
        val += c
    top = max(contribs.items(), key=lambda kv: abs(kv[1]))
    return round(val, 2), top[0], round(top[1], 2), contribs


players = spark.sql(f"SELECT player_id, name, tier, gpr, age, minutes, months_left, wage_per_yr, gpv "
                    f"FROM {CATALOG}.{SCHEMA}.players").toPandas()

# ---- player_valuation ----
rows = []
val_by = {}
for _, p in players.iterrows():
    v, tf, tc, contribs = score(p)
    val_by[p.player_id] = v
    rows.append({"player_id": p.player_id, "name": p["name"], "tier": p.tier,
                 "model_value": v, "gpv": float(p.gpv), "base_value": COEF["base"],
                 "top_driver": tf, "top_contribution": tc, "contributions_json": json.dumps(contribs)})
pv = spark.createDataFrame(pd.DataFrame(rows))
pv.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.player_valuation")
spark.sql(f"COMMENT ON TABLE {CATALOG}.{SCHEMA}.player_valuation IS 'What-if valuation model output per player (€M) with the dominant driver; served live by the acme-valuation endpoint.'")

# ---- read scenarios + moves from Lakebase ----
w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
tok = w.api_client.do("POST", "/api/2.0/database/credentials",
                      body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]
conn = psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user, password=tok, sslmode="require")
cur = conn.cursor()
cur.execute(f"SELECT scenario_id, name, created_by, base_formation, notes FROM {APP_SCHEMA}.scenarios ORDER BY created_at")
scen_rows = cur.fetchall()
cur.execute(f"SELECT scenario_id, player_id, action::text, adjusted_wage, adjusted_value, note FROM {APP_SCHEMA}.scenario_moves ORDER BY scenario_id, move_id")
move_rows = cur.fetchall()
cur.close(); conn.close()

pmeta = {p.player_id: p for _, p in players.iterrows()}
base_value = round(sum(val_by.values()), 1)
base_wage = round(float(players.wage_per_yr.fillna(0).sum()), 1)

impact_rows, move_out = [], []
moves_by = {}
for sid, pid, act, aw, av, note in move_rows:
    moves_by.setdefault(sid, []).append((pid, act, aw, av, note))

for sid, name, cby, form, notes in scen_rows:
    value, wage, n = base_value, base_wage, len(players)
    cap = spend = proceeds = 0.0
    for pid, act, aw, av, note in moves_by.get(sid, []):
        p = pmeta.get(pid)
        cv = val_by.get(pid, 0.0)
        cw = float(p.wage_per_yr) if p is not None and p.wage_per_yr is not None else 0.0
        aw = float(aw or 0); av = float(av or 0)
        vd = wd = cg = 0.0
        if act == "sell":
            value -= cv; wage -= cw; proceeds += av; cap += av - cv; n -= 1; vd = -cv; wd = -cw; cg = av - cv
        elif act == "buy":
            value += av; wage += aw; spend += av; n += 1; vd = av; wd = aw
        elif act == "promote":
            wage += aw - cw; wd = aw - cw
        move_out.append({"scenario_id": sid, "scenario_name": name, "player_id": pid,
                         "player_name": (p["name"] if p is not None else pid), "action": act,
                         "adjusted_wage": aw, "adjusted_value": av, "value_delta": round(vd, 1),
                         "wage_delta": round(wd, 1), "capital_gain": round(cg, 1), "note": note})
    impact_rows.append({"scenario_id": sid, "name": name, "created_by": cby, "base_formation": form,
                        "notes": notes, "squad_value": round(value, 1), "wage_bill": round(wage, 1),
                        "capital_gains": round(cap, 1), "net_spend": round(spend - proceeds, 1),
                        "n_players": n, "squad_value_delta": round(value - base_value, 1),
                        "wage_bill_delta": round(wage - base_wage, 1)})

spark.createDataFrame(pd.DataFrame(impact_rows)).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.scenario_impact")
spark.sql(f"COMMENT ON TABLE {CATALOG}.{SCHEMA}.scenario_impact IS 'What-if squad plans (scenarios) from Lakebase with squad value, wage bill, capital gains and net spend. Baseline (Current) squad value={base_value} EUR M, wage bill={base_wage} EUR M.'")
spark.createDataFrame(pd.DataFrame(move_out)).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.scenario_moves")
spark.sql(f"COMMENT ON TABLE {CATALOG}.{SCHEMA}.scenario_moves IS 'Per-player moves (sell/buy/promote/keep) for each scenario, synced from Lakebase Postgres, with value/wage deltas and capital gain.'")

dbutils.notebook.exit(json.dumps({
    "ok": True, "player_valuation": len(rows), "scenarios": len(impact_rows), "moves": len(move_out),
    "base_value": base_value, "base_wage": base_wage,
    "impact": impact_rows}, default=str))

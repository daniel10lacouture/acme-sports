# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase read — direct Postgres proof of scenarios + scenario_moves
# MAGIC Read-only. Connects to the `acme-lakebase` Postgres instance with an OAuth token
# MAGIC (same pattern the app SP uses) and dumps `acme_app.scenarios` +
# MAGIC `acme_app.scenario_moves` so we can prove app writes/deletes actually land in
# MAGIC Postgres. Never writes.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, uuid, psycopg2
from databricks.sdk import WorkspaceClient

INSTANCE, APP_DB, APP_SCHEMA = "acme-lakebase", "acme", "acme_app"

w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
token = w.api_client.do("POST", "/api/2.0/database/credentials",
                        body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]

conn = psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user,
                        password=token, sslmode="require")
cur = conn.cursor()
cur.execute(f"SELECT scenario_id, name, created_by, created_at::text FROM {APP_SCHEMA}.scenarios ORDER BY created_at")
scen = [dict(zip(["scenario_id", "name", "created_by", "created_at"], r)) for r in cur.fetchall()]
cur.execute(f"SELECT scenario_id, count(*) FROM {APP_SCHEMA}.scenario_moves GROUP BY 1")
mv = {r[0]: int(r[1]) for r in cur.fetchall()}
for s in scen:
    s["n_moves"] = mv.get(s["scenario_id"], 0)
# full move detail for any scenario id passed in via widget (default: none)
try:
    focus = dbutils.widgets.get("focus")
except Exception:
    focus = "scn_delverify_v1"
detail = []
if focus:
    cur.execute(f"SELECT player_id, action::text, adjusted_wage, adjusted_value, note "
                f"FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s ORDER BY move_id", (focus,))
    detail = [dict(zip(["player_id", "action", "adjusted_wage", "adjusted_value", "note"], r)) for r in cur.fetchall()]
conn.close()

dbutils.notebook.exit(json.dumps({"scenarios": scen, "focus": focus, "focus_moves": detail}, default=str))

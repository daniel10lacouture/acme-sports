# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase cleanup — remove verification test scenarios
# MAGIC Deletes `scn_check_run` (written by check_run.py) and `scn_demoprep` (demo-prep
# MAGIC human-path verification) from `acme_app.scenarios` + `scenario_moves`, so the
# MAGIC Planning tab shows ONLY the intended demo Scenario B. Idempotent / safe re-run.
# MAGIC Never touches `scn_b_saliba_dowman`.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid, psycopg2
from databricks.sdk import WorkspaceClient

INSTANCE, APP_DB, APP_SCHEMA = "acme-lakebase", "acme", "acme_app"
DROP = ("scn_check_run", "scn_demoprep")

w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
token = w.api_client.do("POST", "/api/2.0/database/credentials",
                        body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]

conn = psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user,
                        password=token, sslmode="require")
with conn:
    cur = conn.cursor()
    for sid in DROP:
        cur.execute(f"DELETE FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s", (sid,))
        cur.execute(f"DELETE FROM {APP_SCHEMA}.scenarios WHERE scenario_id=%s", (sid,))
    cur.execute(f"SELECT scenario_id, name FROM {APP_SCHEMA}.scenarios ORDER BY created_at")
    remaining = cur.fetchall()
conn.close()

dbutils.notebook.exit("remaining scenarios: " + str(remaining))

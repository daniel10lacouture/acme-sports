# Databricks notebook source
# MAGIC %md
# MAGIC # L0 — Lakebase transactional round-trip (de-risk)
# MAGIC Proves the Lakebase (Provisioned, Public Preview) read/write path on FEVM
# MAGIC `fevm-classic-stable-9cgeia` **before** any app/UI is built.
# MAGIC
# MAGIC Runs on **serverless** (has PyPI access → installs `psycopg2-binary`, which will
# MAGIC not pip-install locally). Connects with an **OAuth token from the Databricks SDK**
# MAGIC — the exact pattern the Databricks App will reuse later.
# MAGIC
# MAGIC Steps: create OLTP DB `acme` → schema `acme_app` → tables `scenarios`,
# MAGIC `scenario_moves` → INSERT "Scenario B" + moves → SELECT back. Idempotent (safe re-run).

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, uuid, psycopg2
from databricks.sdk import WorkspaceClient

INSTANCE = "acme-lakebase"
APP_DB   = "acme"        # OLTP database inside the instance
APP_SCHEMA = "acme_app"  # app-OLTP schema

# The serverless databricks-sdk build here predates the typed `w.database` client, and
# the notebook CommandContext tags() are not whitelisted on serverless. So use the SDK's
# generic REST caller `api_client.do()` — it resolves the workspace host + auth itself and
# can hit the Database Instances (Public Preview) endpoints directly.
w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
token = w.api_client.do("POST", "/api/2.0/database/credentials",
                        body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]
print(f"instance={INSTANCE} host={host} user={user} state={inst.get('state')}")

def connect(dbname):
    return psycopg2.connect(host=host, port=5432, dbname=dbname, user=user,
                            password=token, sslmode="require")

# COMMAND ----------

# 1) Create the OLTP database `acme` if it does not already exist (additive; never drops).
conn = connect("postgres"); conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (APP_DB,))
if cur.fetchone() is None:
    cur.execute(f'CREATE DATABASE "{APP_DB}"')
    print(f"created database {APP_DB}")
else:
    print(f"database {APP_DB} already exists — reusing")
cur.close(); conn.close()

# COMMAND ----------

# 2) Schema + transactional tables (model of their "Create Scenario" feature). All IF NOT EXISTS.
conn = connect(APP_DB); conn.autocommit = True
cur = conn.cursor()
cur.execute(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}")

# action ENUM: keep / sell / promote / buy  (guarded create — no error if it exists)
cur.execute(f"""
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                 WHERE t.typname='move_action' AND n.nspname='{APP_SCHEMA}') THEN
    CREATE TYPE {APP_SCHEMA}.move_action AS ENUM ('keep','sell','promote','buy');
  END IF;
END $$;
""")

cur.execute(f"""
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.scenarios (
    scenario_id    TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    created_by     TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    base_formation TEXT,
    notes          TEXT
);
""")

cur.execute(f"""
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.scenario_moves (
    move_id        BIGSERIAL PRIMARY KEY,
    scenario_id    TEXT NOT NULL REFERENCES {APP_SCHEMA}.scenarios(scenario_id) ON DELETE CASCADE,
    player_id      TEXT NOT NULL,
    action         {APP_SCHEMA}.move_action NOT NULL,
    adjusted_wage  DOUBLE PRECISION,
    adjusted_value DOUBLE PRECISION,
    note           TEXT
);
""")
print("schema + tables ready")
cur.close(); conn.close()

# COMMAND ----------

# 3) Transactional write: INSERT a scenario + its moves in a single committed transaction.
#    Idempotent so re-running the notebook does not error or duplicate.
SCENARIO_ID = "scn_b_saliba_dowman"
conn = connect(APP_DB)
try:
    with conn:  # transaction — commits on success, rolls back on exception
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO {APP_SCHEMA}.scenarios (scenario_id, name, created_by, base_formation, notes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (scenario_id) DO UPDATE
              SET name=EXCLUDED.name, created_by=EXCLUDED.created_by,
                  base_formation=EXCLUDED.base_formation, notes=EXCLUDED.notes;
        """, (SCENARIO_ID, "Scenario B - Sell Saliba, promote Dowman", user,
              "4-3-3", "What-if: fund the rebuild by selling Saliba; promote Dowman from the academy."))

        # rewrite this scenario's moves cleanly (delete-then-insert within the txn)
        cur.execute(f"DELETE FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s", (SCENARIO_ID,))
        moves = [
            (SCENARIO_ID, "p_saliba", "sell",    0.0, 90.0, "Sell at ~est valuation high to fund rebuild"),
            (SCENARIO_ID, "p_dowman", "promote", 1.5,  8.0, "Promote from academy to first team; wage bump 0.2 -> 1.5"),
        ]
        cur.executemany(f"""
            INSERT INTO {APP_SCHEMA}.scenario_moves
              (scenario_id, player_id, action, adjusted_wage, adjusted_value, note)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, moves)
    print(f"committed scenario {SCENARIO_ID} + {len(moves)} moves")
finally:
    conn.close()

# COMMAND ----------

# 4) Read it back (transactional round-trip proof).
conn = connect(APP_DB)
cur = conn.cursor()
cur.execute(f"""
  SELECT scenario_id, name, created_by, created_at, base_formation, notes
  FROM {APP_SCHEMA}.scenarios WHERE scenario_id=%s
""", (SCENARIO_ID,))
srow = cur.fetchone()
scenario = {
    "scenario_id": srow[0], "name": srow[1], "created_by": srow[2],
    "created_at": str(srow[3]), "base_formation": srow[4], "notes": srow[5],
}

cur.execute(f"""
  SELECT player_id, action::text, adjusted_wage, adjusted_value, note
  FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s ORDER BY move_id
""", (SCENARIO_ID,))
moves_read = [
    {"player_id": r[0], "action": r[1], "adjusted_wage": r[2],
     "adjusted_value": r[3], "note": r[4]} for r in cur.fetchall()
]
cur.close(); conn.close()

result = {
    "ok": True,
    "instance": INSTANCE, "host": host, "db": APP_DB, "schema": APP_SCHEMA,
    "user": user,
    "connection_method": "serverless notebook + psycopg2-binary + Databricks SDK OAuth token",
    "scenario_written_and_read": scenario,
    "moves_written_and_read": moves_read,
    "moves_count": len(moves_read),
}
print(json.dumps(result, indent=2))

# COMMAND ----------

dbutils.notebook.exit(json.dumps(result))

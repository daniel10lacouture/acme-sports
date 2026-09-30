# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase grants — let the app service principal use the OLTP + synced tables
# MAGIC The `acme-sports` app connects to `acme-lakebase` as its own service principal
# MAGIC via OAuth (the proven L0 pattern). This grants PUBLIC (all roles, incl. the SP's
# MAGIC OAuth-provisioned role) read/write on the demo DB `acme`. Safe: `acme` is an
# MAGIC isolated demo instance holding only this demo's data. Idempotent.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid, psycopg2
from databricks.sdk import WorkspaceClient
INSTANCE, APP_DB = "acme-lakebase", "acme"
w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
token = w.api_client.do("POST", "/api/2.0/database/credentials",
                        body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]
conn = psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user, password=token, sslmode="require")
conn.autocommit = True
cur = conn.cursor()

stmts = [
    "GRANT CONNECT ON DATABASE acme TO PUBLIC",
    "GRANT USAGE ON SCHEMA acme_app TO PUBLIC",
    "GRANT USAGE ON SCHEMA public TO PUBLIC",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA acme_app TO PUBLIC",
    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA acme_app TO PUBLIC",
    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO PUBLIC",
    "GRANT USAGE ON TYPE acme_app.move_action TO PUBLIC",
    # future objects created by this owner:
    "ALTER DEFAULT PRIVILEGES IN SCHEMA acme_app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA acme_app GRANT USAGE, SELECT ON SEQUENCES TO PUBLIC",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO PUBLIC",
]
for s in stmts:
    cur.execute(s); print("ok:", s)

cur.close(); conn.close()
dbutils.notebook.exit("grants applied")

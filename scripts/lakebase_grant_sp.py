# Databricks notebook source
# MAGIC %md
# MAGIC # Register the app service principal as a Postgres role (OAuth login)
# MAGIC The `acme-sports` app connects to Lakebase as its own SP via OAuth. The SP has
# MAGIC CAN_USE on the instance (so it can mint a DB credential), but Postgres also needs a
# MAGIC matching **login role** named after the SP's identity. Create it as the instance owner
# MAGIC and grant it the demo-DB privileges. Idempotent.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid, psycopg2
from databricks.sdk import WorkspaceClient

INSTANCE, APP_DB, APP_SCHEMA = "acme-lakebase", "acme", "acme_app"
SP_CLIENT_ID = "47b731e0-6bf9-4ac4-923c-b93485795a4a"
SP_NAME = "app-32gfki acme-sports"

w = WorkspaceClient()
inst = w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
host = inst["read_write_dns"]
user = w.current_user.me().user_name
tok = w.api_client.do("POST", "/api/2.0/database/credentials",
                      body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]
conn = psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user, password=tok, sslmode="require")
conn.autocommit = True
cur = conn.cursor()

created = []
# Databricks Lakebase: databricks_create_role() registers a Databricks identity as a PG
# role that accepts OAuth tokens. Try it for both the client_id and the SP display name;
# fall back to a plain LOGIN role if the helper isn't present.
for ident in (SP_CLIENT_ID, SP_NAME):
    try:
        cur.execute("SELECT databricks_create_role(%s, %s)", (ident, "SERVICE_PRINCIPAL"))
        created.append(f"databricks_create_role({ident})")
    except Exception as e:
        conn.rollback() if not conn.autocommit else None
        try:
            cur.execute(f'CREATE ROLE "{ident}" WITH LOGIN')
            created.append(f"CREATE ROLE {ident}")
        except Exception as e2:
            created.append(f"{ident}: exists/err {str(e2)[:60]}")

# grant privileges to the SP role(s) explicitly (in addition to PUBLIC)
for ident in (SP_CLIENT_ID, SP_NAME):
    for stmt in [
        f'GRANT CONNECT ON DATABASE acme TO "{ident}"',
        f'GRANT USAGE ON SCHEMA {APP_SCHEMA} TO "{ident}"',
        f'GRANT USAGE ON SCHEMA public TO "{ident}"',
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {APP_SCHEMA} TO "{ident}"',
        f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {APP_SCHEMA} TO "{ident}"',
        f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{ident}"',
        f'GRANT USAGE ON TYPE {APP_SCHEMA}.move_action TO "{ident}"',
    ]:
        try:
            cur.execute(stmt)
        except Exception as e:
            pass

cur.execute("SELECT rolname FROM pg_roles WHERE rolname IN (%s,%s)", (SP_CLIENT_ID, SP_NAME))
roles = [r[0] for r in cur.fetchall()]
cur.close(); conn.close()
import json
dbutils.notebook.exit(json.dumps({"created": created, "roles_present": roles}))

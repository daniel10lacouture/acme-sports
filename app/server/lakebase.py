"""Lakebase (Postgres) transactional access for the Acme Sports app.

Implements the exact pattern proven in scripts/lakebase_l0_roundtrip.py:
  host  <- GET  /api/2.0/database/instances/{name}
  token <- POST /api/2.0/database/credentials   (OAuth, ~1h TTL)
  user  <- current_user.me().user_name          (app service principal identity)
  psycopg2.connect(host, 5432, dbname, user, password=token, sslmode='require')

In Databricks Apps the WorkspaceClient authenticates as the app service principal,
which has CAN_USE on the `acme-lakebase` instance and PUBLIC grants on the `acme`
demo DB. Credentials are cached and regenerated on TTL/expiry; connections are opened
per request with one automatic retry on an auth/connection error.
"""
import os, time, uuid, threading
import psycopg2
from server import dbx  # reuse the app's WorkspaceClient (SP-authenticated in Apps)

INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "acme-lakebase")
APP_DB = os.environ.get("LAKEBASE_DB", "acme")
APP_SCHEMA = os.environ.get("LAKEBASE_SCHEMA", "acme_app")
_CRED_TTL = 40 * 60  # regenerate the OAuth DB credential well before its ~1h expiry

# Seeded demo scenarios — PROTECTED / locked: never deletable through the app.
# "Current" is not a Lakebase row (it's the live squad baseline), so only the pre-seeded
# Scenario B (and the mock Scenario A, if present) are guarded here. Everything else is a
# user-created scenario and may be deleted.
SEEDED_SCENARIOS = {"scn_b_saliba_dowman", "scn_a_alvarez"}


def is_seeded(scenario_id):
    return scenario_id in SEEDED_SCENARIOS

_lock = threading.Lock()
_cache = {"host": None, "user": None, "token": None, "ts": 0.0}


def _creds(force=False):
    with _lock:
        if (not force and _cache["token"] and (time.time() - _cache["ts"] < _CRED_TTL)):
            return _cache["host"], _cache["user"], _cache["token"]
        inst = dbx.w.api_client.do("GET", f"/api/2.0/database/instances/{INSTANCE}")
        host = inst["read_write_dns"]
        user = os.environ.get("LAKEBASE_PG_USER") or dbx.w.current_user.me().user_name
        token = dbx.w.api_client.do(
            "POST", "/api/2.0/database/credentials",
            body={"request_id": str(uuid.uuid4()), "instance_names": [INSTANCE]})["token"]
        _cache.update(host=host, user=user, token=token, ts=time.time())
        return host, user, token


def _connect(force=False):
    host, user, token = _creds(force=force)
    return psycopg2.connect(host=host, port=5432, dbname=APP_DB, user=user,
                            password=token, sslmode="require", connect_timeout=15)


def _run(fn):
    """Run fn(conn) with one retry that refreshes the credential on auth/conn error."""
    try:
        conn = _connect()
    except psycopg2.OperationalError:
        conn = _connect(force=True)
    try:
        return fn(conn)
    except psycopg2.OperationalError:
        conn.close()
        conn = _connect(force=True)
        return fn(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------- reads ----------
def list_scenarios():
    def q(conn):
        cur = conn.cursor()
        cur.execute(f"""
          SELECT s.scenario_id, s.name, s.created_by, s.created_at, s.base_formation, s.notes,
                 COALESCE(m.n, 0) AS n_moves
          FROM {APP_SCHEMA}.scenarios s
          LEFT JOIN (SELECT scenario_id, count(*) n FROM {APP_SCHEMA}.scenario_moves GROUP BY 1) m
            USING (scenario_id)
          ORDER BY s.created_at""")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) | {"created_at": str(r[3]), "seeded": is_seeded(r[0])}
                for r in cur.fetchall()]
    return _run(q)


def get_scenario(scenario_id):
    def q(conn):
        cur = conn.cursor()
        cur.execute(f"SELECT scenario_id, name, created_by, created_at, base_formation, notes "
                    f"FROM {APP_SCHEMA}.scenarios WHERE scenario_id=%s", (scenario_id,))
        row = cur.fetchone()
        if not row:
            return None
        scenario = {"scenario_id": row[0], "name": row[1], "created_by": row[2],
                    "created_at": str(row[3]), "base_formation": row[4], "notes": row[5]}
        cur.execute(f"SELECT player_id, action::text, adjusted_wage, adjusted_value, note "
                    f"FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s ORDER BY move_id",
                    (scenario_id,))
        scenario["moves"] = [
            {"player_id": r[0], "action": r[1], "adjusted_wage": r[2],
             "adjusted_value": r[3], "note": r[4]} for r in cur.fetchall()]
        return scenario
    return _run(q)


# ---------- transactional write ----------
def save_scenario(payload):
    sid = (payload.get("scenario_id") or "scn_" + uuid.uuid4().hex[:10]).strip()
    name = (payload.get("name") or "Untitled scenario").strip()
    created_by = (payload.get("created_by") or "app").strip()
    formation = payload.get("base_formation") or "4-3-3"
    notes = payload.get("notes") or ""
    moves = payload.get("moves") or []

    def tx(conn):
        with conn:  # single committed transaction
            cur = conn.cursor()
            cur.execute(f"""
              INSERT INTO {APP_SCHEMA}.scenarios (scenario_id, name, created_by, base_formation, notes)
              VALUES (%s, %s, %s, %s, %s)
              ON CONFLICT (scenario_id) DO UPDATE
                SET name=EXCLUDED.name, base_formation=EXCLUDED.base_formation, notes=EXCLUDED.notes
            """, (sid, name, created_by, formation, notes))
            cur.execute(f"DELETE FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s", (sid,))
            for m in moves:
                cur.execute(f"""
                  INSERT INTO {APP_SCHEMA}.scenario_moves
                    (scenario_id, player_id, action, adjusted_wage, adjusted_value, note)
                  VALUES (%s, %s, %s, %s, %s, %s)
                """, (sid, m["player_id"], (m.get("action") or "keep"),
                      m.get("adjusted_wage"), m.get("adjusted_value"), m.get("note")))
        return sid
    _run(tx)
    return get_scenario(sid)


# ---------- transactional delete (protected) ----------
class SeededScenarioError(Exception):
    """Raised when a delete is attempted on a protected/seeded scenario."""


def delete_scenario(scenario_id):
    """Transactionally remove a scenario and cascade its child moves from Lakebase Postgres.

    Refuses to touch seeded/demo scenarios. Returns a dict with the rows removed (for proof)
    or {"found": False} if the id did not exist.
    """
    sid = (scenario_id or "").strip()
    if is_seeded(sid):
        raise SeededScenarioError(sid)

    def tx(conn):
        with conn:  # single committed transaction — children then parent (explicit cascade)
            cur = conn.cursor()
            cur.execute(f"SELECT 1 FROM {APP_SCHEMA}.scenarios WHERE scenario_id=%s", (sid,))
            if cur.fetchone() is None:
                return {"found": False, "scenario_id": sid}
            cur.execute(f"DELETE FROM {APP_SCHEMA}.scenario_moves WHERE scenario_id=%s", (sid,))
            moves_deleted = cur.rowcount
            cur.execute(f"DELETE FROM {APP_SCHEMA}.scenarios WHERE scenario_id=%s", (sid,))
            scen_deleted = cur.rowcount
        return {"found": True, "scenario_id": sid,
                "scenarios_deleted": scen_deleted, "moves_deleted": moves_deleted}
    return _run(tx)


def health():
    """Lightweight connectivity probe for /api/health and check_run."""
    def q(conn):
        cur = conn.cursor()
        cur.execute(f"SELECT count(*) FROM {APP_SCHEMA}.scenarios")
        return {"ok": True, "instance": INSTANCE, "db": APP_DB, "schema": APP_SCHEMA,
                "scenarios": int(cur.fetchone()[0])}
    return _run(q)

#!/usr/bin/env python3
"""Run SQL against the Genie-Warehouse via the Databricks Statement Execution API.

Usage:
  python3 dbsql.py "SELECT 1"
  echo "SELECT 1" | python3 dbsql.py -
  python3 dbsql.py -f path/to/file.sql
Reads via the databricks CLI profile (fe-vm-classic-stable-9cgeia).
"""
import json, subprocess, sys, time, os

PROFILE = "fe-vm-classic-stable-9cgeia"
WAREHOUSE_ID = "84c07276d33bc0a0"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}


def api(method, path, payload=None):
    cmd = ["databricks", "api", method.lower(), path, "-p", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        raise RuntimeError(f"API {method} {path} failed:\n{r.stderr}\n{r.stdout}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def run_sql(stmt, catalog=None, schema=None):
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": stmt,
        "wait_timeout": "30s",
        "on_wait_timeout": "CONTINUE",
    }
    if catalog:
        payload["catalog"] = catalog
    if schema:
        payload["schema"] = schema
    resp = api("POST", "/api/2.0/sql/statements", payload)
    sid = resp["statement_id"]
    state = resp["status"]["state"]
    while state in ("PENDING", "RUNNING"):
        time.sleep(2)
        resp = api("GET", f"/api/2.0/sql/statements/{sid}")
        state = resp["status"]["state"]
    if state != "SUCCEEDED":
        err = resp.get("status", {}).get("error", {})
        raise RuntimeError(f"SQL {state}: {err.get('message','')}\nSTMT: {stmt[:400]}")
    return resp


def run(stmt, catalog=None, schema=None):
    """Execute one statement; return the raw response."""
    return run_sql(stmt, catalog, schema)


def query_rows(stmt, catalog=None, schema=None):
    """Execute a query; return a list of dict rows (column name -> value)."""
    resp = run_sql(stmt, catalog, schema)
    cols = [c["name"] for c in resp.get("manifest", {}).get("schema", {}).get("columns", [])]
    data = resp.get("result", {}).get("data_array", []) or []
    return [dict(zip(cols, r)) for r in data]


def fmt(resp):
    result = resp.get("result", {})
    schema = resp.get("manifest", {}).get("schema", {}).get("columns", [])
    cols = [c["name"] for c in schema]
    rows = result.get("data_array", [])
    out = []
    if cols:
        out.append(" | ".join(cols))
    for row in rows:
        out.append(" | ".join("NULL" if v is None else str(v) for v in row))
    n = resp.get("manifest", {}).get("total_row_count", len(rows))
    out.append(f"[rows: {n}]")
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    catalog = schema = None
    if "--catalog" in args:
        i = args.index("--catalog"); catalog = args[i+1]; del args[i:i+2]
    if "--schema" in args:
        i = args.index("--schema"); schema = args[i+1]; del args[i:i+2]
    if args and args[0] == "-f":
        stmt = open(args[1]).read()
    elif args and args[0] == "-":
        stmt = sys.stdin.read()
    else:
        stmt = " ".join(args)
    # Split on ';' but not inside single-quoted strings or line comments.
    def split_sql(text):
        out, cur, in_str, i = [], [], False, 0
        while i < len(text):
            c = text[i]
            if c == "'":
                in_str = not in_str
                cur.append(c)
            elif c == "-" and not in_str and i + 1 < len(text) and text[i+1] == "-":
                # line comment: copy to end of line
                j = text.find("\n", i)
                j = len(text) if j == -1 else j
                cur.append(text[i:j]); i = j; continue
            elif c == ";" and not in_str:
                s = "".join(cur).strip()
                if s:
                    out.append(s)
                cur = []
            else:
                cur.append(c)
            i += 1
        s = "".join(cur).strip()
        if s:
            out.append(s)
        return out
    parts = split_sql(stmt)
    if len(parts) > 1:
        for p in parts:
            resp = run_sql(p, catalog, schema)
            print(fmt(resp))
            print("---")
    else:
        resp = run_sql(stmt, catalog, schema)
        print(fmt(resp))

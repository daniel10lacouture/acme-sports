# Databricks notebook source
# MAGIC %md
# MAGIC # 🩺 Whoop connector — LIVE ingestion path (placeholder / swap-to-real)
# MAGIC
# MAGIC The AI Physio / Load Manager runs today on **synthetic, schema-representative** data
# MAGIC (`scripts/physio_data.sql` → `whoop_daily`, `statsports_sessions`). This notebook is the
# MAGIC **real connector**: it is wired to the actual Whoop Developer API and writes into the
# MAGIC **same `whoop_daily` schema**, so flipping to live data is a credentials swap — no app or
# MAGIC model change. (Same "one config away" pattern as the Whisper transcription path.)
# MAGIC
# MAGIC **Why it's a placeholder here:** Whoop is **per-athlete consumer biometrics**. A live team
# MAGIC feed needs (1) a **registered Whoop developer app** (`client_id`/`client_secret`), and
# MAGIC (2) each player to complete **OAuth consent** so we hold their access/refresh token. We have
# MAGIC neither in this FEVM (and using real athletes' data would be a privacy issue), so this cell
# MAGIC **detects missing credentials and no-ops** rather than failing — the synthetic table stands.
# MAGIC
# MAGIC Reachability was verified: `https://api.prod.whoop.com` responds (401 without a token) and the
# MAGIC OAuth endpoint is live — so only the account + consent tokens are missing.
# MAGIC
# MAGIC **To go live:** register the app at developer.whoop.com, store the secrets below, populate the
# MAGIC `whoop_athlete_tokens` table with each player's OAuth token, and run.

# COMMAND ----------

import json, time, urllib.request, urllib.parse, datetime
from pyspark.sql import functions as F, types as T

CATALOG, SCHEMA = "acme_sports", "demo"
WHOOP_BASE = "https://api.prod.whoop.com"
TOKEN_URL  = f"{WHOOP_BASE}/oauth/oauth2/token"
SCOPES = "read:recovery read:sleep read:cycles read:profile"

# Credentials come from a Databricks secret scope (never hard-code). Missing -> placeholder mode.
try:
    CLIENT_ID     = dbutils.secrets.get("whoop", "client_id")
    CLIENT_SECRET = dbutils.secrets.get("whoop", "client_secret")
    HAVE_CREDS = bool(CLIENT_ID and CLIENT_SECRET)
except Exception:
    CLIENT_ID = CLIENT_SECRET = None
    HAVE_CREDS = False

# Per-athlete OAuth tokens (one row per consented player). In live mode this table is populated
# by the consent flow (authorization_code grant + refresh). Schema:
#   player_id STRING, whoop_user_id STRING, access_token STRING, refresh_token STRING, expires_at TIMESTAMP
TOKENS_TABLE = f"{CATALOG}.{SCHEMA}.whoop_athlete_tokens"


def _get(url, token, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def refresh_access_token(refresh_token):
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "scope": SCOPES,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def fetch_athlete_daily(player_id, access_token, days=30):
    """Pull recovery + sleep + cycle for the window and map to the whoop_daily schema."""
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat() + "Z"
    recovery = _get(f"{WHOOP_BASE}/developer/v1/recovery",        access_token, {"start": start, "limit": 25})
    sleep    = _get(f"{WHOOP_BASE}/developer/v1/activity/sleep",  access_token, {"start": start, "limit": 25})
    cycle    = _get(f"{WHOOP_BASE}/developer/v1/cycle",           access_token, {"start": start, "limit": 25})
    # index by calendar date
    sleep_by_day = {s["start"][:10]: s for s in sleep.get("records", [])}
    cycle_by_day = {c["start"][:10]: c for c in cycle.get("records", [])}
    rows = []
    for r in recovery.get("records", []):
        day = r["created_at"][:10]
        sc = r.get("score", {}) or {}
        sl = (sleep_by_day.get(day, {}).get("score", {}) or {})
        cy = (cycle_by_day.get(day, {}).get("score", {}) or {})
        rows.append({
            "player_id": player_id, "metric_date": day,
            "sleep_hours": round((sl.get("stage_summary", {}).get("total_in_bed_time_milli", 0) or 0) / 3.6e6, 1),
            "sleep_performance_pct": int(sl.get("sleep_performance_percentage") or 0),
            "hrv_ms": int((sc.get("hrv_rmssd_milli") or 0)),
            "resting_hr": int(sc.get("resting_heart_rate") or 0),
            "day_strain": round(float(cy.get("strain") or 0), 1),
            "recovery_pct": int(sc.get("recovery_score") or 0),
        })
    return rows

# COMMAND ----------

if not HAVE_CREDS:
    print("⚪ PLACEHOLDER MODE — no Whoop credentials in secret scope 'whoop'.")
    print("   The Physio assistant continues on the synthetic whoop_daily table.")
    print("   To go live: register a Whoop developer app, add secrets whoop/client_id +")
    print("   whoop/client_secret, populate", TOKENS_TABLE, "with consented athlete tokens, re-run.")
    dbutils.notebook.exit(json.dumps({"mode": "placeholder", "wrote_rows": 0}))

# ---- LIVE MODE (runs only when credentials + athlete tokens exist) ----
tokens = spark.table(TOKENS_TABLE).collect()
all_rows = []
for t in tokens:
    tok = t["access_token"]
    if t["expires_at"] and t["expires_at"] < datetime.datetime.utcnow():
        tok = refresh_access_token(t["refresh_token"])["access_token"]  # (persist back in real impl)
    all_rows += fetch_athlete_daily(t["player_id"], tok, days=30)

schema = T.StructType([
    T.StructField("player_id", T.StringType()), T.StructField("metric_date", T.StringType()),
    T.StructField("sleep_hours", T.DoubleType()), T.StructField("sleep_performance_pct", T.IntegerType()),
    T.StructField("hrv_ms", T.IntegerType()), T.StructField("resting_hr", T.IntegerType()),
    T.StructField("day_strain", T.DoubleType()), T.StructField("recovery_pct", T.IntegerType()),
])
df = (spark.createDataFrame(all_rows, schema)
      .withColumn("metric_date", F.to_date("metric_date"))
      .join(spark.table(f"{CATALOG}.{SCHEMA}.players").select("player_id", F.col("name").alias("player_name")),
            "player_id", "left"))
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.whoop_daily")
print(f"🟢 LIVE — wrote {df.count()} Whoop rows for {len(tokens)} athletes.")
dbutils.notebook.exit(json.dumps({"mode": "live", "wrote_rows": df.count()}))

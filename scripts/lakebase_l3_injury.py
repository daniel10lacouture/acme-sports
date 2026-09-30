# Databricks notebook source
# MAGIC %md
# MAGIC # L3 — Injury & load-risk model
# MAGIC Transparent load-risk model over **synthetic physical / tracking data** (recent minutes
# MAGIC load, sprint & high-accel counts, match density, age, injury history). Produces an
# MAGIC interpretable 0–100 risk score → band → availability recommendation, materialized into a
# MAGIC **new additive Delta table** `acme_sports.demo.injury_risk` (the 4 existing tables are
# MAGIC untouched). The model is also logged to MLflow/UC for lineage. Planning reads this table
# MAGIC for availability, and it is added to the Acme Scout Genie space in L4.
# MAGIC
# MAGIC Synthetic tracking is deterministic (seeded by player_id) so scores are stable across runs.

# COMMAND ----------

# MAGIC %pip install mlflow --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, hashlib, mlflow
import pandas as pd
from pyspark.sql import functions as F

CATALOG, SCHEMA = "acme_sports", "demo"
TABLE = f"{CATALOG}.{SCHEMA}.injury_risk"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.acme_injury_risk"

players = spark.sql(f"SELECT player_id, name, age, minutes, tier FROM {CATALOG}.{SCHEMA}.players").toPandas()


def seed(pid, salt):
    return int(hashlib.md5(f"{pid}:{salt}".encode()).hexdigest(), 16) % 1000 / 1000.0


def synth(row):
    pid, age, mins = row["player_id"], int(row["age"]), int(row["minutes"] or 0)
    # recent minutes load = last-4-matches minutes, correlated with season minutes
    recent_load = int(min(360, mins / 34 * 4 * (0.75 + 0.5 * seed(pid, "load"))))
    sprints_per90 = round(14 + 12 * seed(pid, "spr"), 1)          # 14–26
    high_accel_per90 = round(28 + 22 * seed(pid, "acc"), 1)       # 28–50
    match_density_14d = int(2 + round(2 * seed(pid, "den")))      # 2–4 games / 14d
    prior_injuries = int(round(3 * seed(pid, "hist") + (1 if age >= 30 else 0)))  # 0–4
    return pd.Series({"recent_minutes_load": recent_load, "sprints_per90": sprints_per90,
                      "high_accel_per90": high_accel_per90, "match_density_14d": match_density_14d,
                      "prior_injuries": prior_injuries})


feat = players.join(players.apply(synth, axis=1))

# ---- transparent additive risk model (0..100) ----
WEIGHTS = {"intercept": 18.0, "age_over_27": 2.6, "load_over_200": 0.10,
           "density_over_2": 5.0, "prior_injuries": 7.5, "accel_over_35": 0.9, "sprints_over_20": 0.8}


def risk_row(r):
    c = {
        "age": WEIGHTS["age_over_27"] * max(0, r["age"] - 27),
        "recent load": WEIGHTS["load_over_200"] * max(0, r["recent_minutes_load"] - 200),
        "match density": WEIGHTS["density_over_2"] * max(0, r["match_density_14d"] - 2),
        "injury history": WEIGHTS["prior_injuries"] * r["prior_injuries"],
        "high accelerations": WEIGHTS["accel_over_35"] * max(0, r["high_accel_per90"] - 35),
        "sprint volume": WEIGHTS["sprints_over_20"] * max(0, r["sprints_per90"] - 20),
    }
    score = max(3, min(95, WEIGHTS["intercept"] + sum(c.values())))
    band = ("High" if score >= 72 else "Elevated" if score >= 55 else "Moderate" if score >= 38 else "Low")
    avail = ("Doubtful" if band == "High" else "Monitor" if band == "Elevated" else "Available")
    drivers = sorted(c.items(), key=lambda kv: -kv[1])
    top = drivers[0][0]
    note = {"High": f"Manage load — {top} elevated; consider rotation.",
            "Elevated": f"Monitor {top}; limit high-intensity exposure.",
            "Moderate": "Within normal range; routine monitoring.",
            "Low": "Low load-risk; fully available."}[band]
    return pd.Series({"risk_score": round(score, 1), "risk_band": band, "availability": avail,
                      "top_factor": top, "risk_note": note,
                      "contributions_json": json.dumps({k: round(v, 1) for k, v in c.items()})})


scored = feat.join(feat.apply(risk_row, axis=1))
scored = scored[["player_id", "name", "tier", "age", "recent_minutes_load", "sprints_per90",
                 "high_accel_per90", "match_density_14d", "prior_injuries",
                 "risk_score", "risk_band", "availability", "top_factor", "risk_note",
                 "contributions_json"]]

# ---- write NEW Delta table (additive; CREATE OR REPLACE only this new table) ----
sdf = spark.createDataFrame(scored)
sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(TABLE)
spark.sql(f"COMMENT ON TABLE {TABLE} IS 'L3 injury & load-risk scores over synthetic tracking data (additive; read by app Planning + Acme Scout Genie).'")
n = spark.table(TABLE).count()

# ---- log the scoring model to MLflow/UC for lineage (not served; scores are materialized) ----
RISK_FEATURES = ["age", "recent_minutes_load", "sprints_per90", "high_accel_per90",
                 "match_density_14d", "prior_injuries"]


class InjuryRiskModel(mlflow.pyfunc.PythonModel):
    def __init__(self, weights):
        self.w = weights

    def predict(self, context, model_input):
        out = []
        for _, r in model_input.iterrows():
            c = {"age": self.w["age_over_27"] * max(0, r["age"] - 27),
                 "recent load": self.w["load_over_200"] * max(0, r["recent_minutes_load"] - 200),
                 "match density": self.w["density_over_2"] * max(0, r["match_density_14d"] - 2),
                 "injury history": self.w["prior_injuries"] * r["prior_injuries"],
                 "high accelerations": self.w["accel_over_35"] * max(0, r["high_accel_per90"] - 35),
                 "sprint volume": self.w["sprints_over_20"] * max(0, r["sprints_per90"] - 20)}
            out.append(max(3, min(95, self.w["intercept"] + sum(c.values()))))
        return out

mlflow.set_registry_uri("databricks-uc")
try:
    from mlflow.models.signature import infer_signature
    ex_in = feat[RISK_FEATURES].astype(float).head(3)
    im = InjuryRiskModel(WEIGHTS)
    ex_out = im.predict(None, ex_in)
    sig = infer_signature(ex_in, ex_out)
    with mlflow.start_run(run_name="acme_injury_risk"):
        mlflow.log_dict(WEIGHTS, "weights.json")
        mlflow.pyfunc.log_model(artifact_path="model", python_model=im, signature=sig,
                                input_example=ex_in, registered_model_name=MODEL_NAME,
                                pip_requirements=["mlflow", "pandas"])
    model_logged = True
except Exception as e:
    model_logged = f"skipped: {str(e)[:80]}"

bands = spark.sql(f"SELECT risk_band, count(*) n FROM {TABLE} GROUP BY risk_band").toPandas().to_dict("records")
top = spark.sql(f"SELECT name, risk_score, risk_band, availability, top_factor FROM {TABLE} ORDER BY risk_score DESC LIMIT 5").toPandas().to_dict("records")
dbutils.notebook.exit(json.dumps({"ok": True, "table": TABLE, "rows": n, "model_logged": model_logged,
                                  "bands": bands, "top5": top}, default=str))

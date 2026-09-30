# Databricks notebook source
# MAGIC %md
# MAGIC # L2 — What-if valuation model on Model Serving (serverless)
# MAGIC Transparent, calibrated linear valuation model over the squad. Predicts a player's
# MAGIC market value (€M) from interpretable features and returns **per-feature contributions**
# MAGIC for explainability (value = league base + Σ contributions). Fit with scikit-learn
# MAGIC (OLS — fully interpretable), logged as an MLflow pyfunc, registered to Unity Catalog,
# MAGIC and deployed to a **serverless Model Serving** endpoint.
# MAGIC
# MAGIC AutoML was considered but rejected: n=20 players makes AutoML search meaningless and
# MAGIC opaque; a calibrated OLS gives honest coefficients AND exact additive explanations,
# MAGIC which is what the player card + scenario impact need.

# COMMAND ----------

# MAGIC %pip install scikit-learn mlflow --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, numpy as np, pandas as pd, mlflow
from sklearn.linear_model import LinearRegression

CATALOG, SCHEMA = "acme_sports", "demo"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.acme_valuation"
ENDPOINT = "acme-valuation"
# Intuitive market-value drivers (quality, age curve, availability, contract leverage).
# Style-fit features are excluded: at n=20 they are collinear and swamp the additive
# explanations, which would muddle the player-card story. GPR should lead.
FEATURES = ["gpr", "age", "minutes", "months_left"]

df = spark.sql(f"""
  SELECT player_id, name, gpr, age, minutes, months_left, team_style_fit, player_style_fit,
         est_valuation_low, est_valuation_high, gpv
  FROM {CATALOG}.{SCHEMA}.players
""").toPandas()
# target = market value = midpoint of the analyst valuation range (independent of GPV alone)
df["target"] = (df["est_valuation_low"] + df["est_valuation_high"]) / 2.0
X = df[FEATURES].astype(float).values
y = df["target"].astype(float).values

reg = LinearRegression().fit(X, y)
means = df[FEATURES].astype(float).mean().to_dict()
coef = {f: float(c) for f, c in zip(FEATURES, reg.coef_)}
base = float(np.mean(y))  # OLS: prediction at feature means == mean(target)
r2 = float(reg.score(X, y))
COEF_BLOB = {"features": FEATURES, "coef": coef, "mean": means, "base": base, "r2": r2}
print("R2:", round(r2, 3))
print(json.dumps(COEF_BLOB, indent=2))

# COMMAND ----------

# ---- MLflow pyfunc: value + additive per-feature contributions ----
class ValuationModel(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        with open(context.artifacts["coef"]) as f:
            self.m = json.load(f)

    def _score_row(self, row):
        m = self.m
        contribs = {}
        val = m["base"]
        for f in m["features"]:
            c = m["coef"][f] * (float(row[f]) - m["mean"][f])
            contribs[f] = round(c, 2)
            val += c
        # drivers sorted by absolute impact (for the UI)
        drivers = sorted(contribs.items(), key=lambda kv: -abs(kv[1]))
        return {"value": round(val, 2), "base": round(m["base"], 2),
                "contributions": contribs,
                "top_drivers": [{"feature": k, "contribution": v} for k, v in drivers]}

    def predict(self, context, model_input):
        if isinstance(model_input, pd.DataFrame):
            rows = model_input.to_dict("records")
        else:
            rows = list(model_input)
        return [self._score_row(r) for r in rows]

# write coef artifact
with open("/tmp/valuation_coef.json", "w") as f:
    json.dump(COEF_BLOB, f)

from mlflow.models.signature import infer_signature
sample = df[FEATURES].astype(float).head(3)
_m = ValuationModel(); _m.m = COEF_BLOB  # set coef directly for local signature computation
example_out = [_m._score_row(r) for r in sample.to_dict("records")]
sig = infer_signature(sample, example_out)

mlflow.set_registry_uri("databricks-uc")
with mlflow.start_run(run_name="acme_valuation_ols") as run:
    mlflow.log_metric("r2", r2)
    mlflow.log_dict(COEF_BLOB, "coefficients.json")
    info = mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=ValuationModel(),
        artifacts={"coef": "/tmp/valuation_coef.json"},
        signature=sig,
        input_example=sample,
        registered_model_name=MODEL_NAME,
        pip_requirements=["mlflow", "pandas", "numpy"],
    )
    run_id = run.info.run_id
print("logged:", info.model_uri, "run:", run_id)

# get the newest registered version
from mlflow.tracking import MlflowClient
c = MlflowClient(registry_uri="databricks-uc")
ver = max(int(v.version) for v in c.search_model_versions(f"name='{MODEL_NAME}'"))
print("registered version:", ver)

# COMMAND ----------

# ---- Deploy to serverless Model Serving ----
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput, ServedEntityInput)
w = WorkspaceClient()

served = ServedEntityInput(entity_name=MODEL_NAME, entity_version=str(ver),
                           scale_to_zero_enabled=True, workload_size="Small")
existing = [e.name for e in (w.serving_endpoints.list() or [])]
if ENDPOINT in existing:
    w.serving_endpoints.update_config(name=ENDPOINT, served_entities=[served])
    print("updated endpoint config:", ENDPOINT)
else:
    w.serving_endpoints.create(name=ENDPOINT,
        config=EndpointCoreConfigInput(served_entities=[served]))
    print("created endpoint:", ENDPOINT)

# COMMAND ----------

# ---- Wait until the NEW config is live (ready + not still updating) + test ----
import time
ready = None
for _ in range(60):
    e = w.serving_endpoints.get(ENDPOINT)
    st = e.state.ready.value if e.state and e.state.ready else "NOT_READY"
    cfg = e.state.config_update.value if e.state and e.state.config_update else "NOT_UPDATING"
    print("state:", st, cfg)
    if st == "READY" and cfg != "IN_PROGRESS":
        ready = True
        break
    time.sleep(20)

test = None
if ready:
    for _ in range(6):  # tolerate a brief window where the old version still answers
        try:
            saka = df[df.player_id == "p_saka"][FEATURES].astype(float).to_dict("records")
            resp = w.serving_endpoints.query(name=ENDPOINT, dataframe_records=saka)
            test = resp.predictions if hasattr(resp, "predictions") else resp.as_dict()
            break
        except Exception as ex:
            test = f"retry: {str(ex)[:80]}"
            time.sleep(15)

dbutils.notebook.exit(json.dumps({
    "ok": bool(ready), "endpoint": ENDPOINT, "model": MODEL_NAME, "version": ver,
    "r2": round(r2, 3), "coefficients": COEF_BLOB, "saka_test": test}, default=str))

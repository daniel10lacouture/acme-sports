# Databricks notebook source
# MAGIC %md
# MAGIC # AI Transfer Assistant — position-specific valuation on Model Serving
# MAGIC A **calibrated, illustrative** valuation model:
# MAGIC `value = position_base + Σ coef·(kpi − ref)` (clamped). Every term is additive and
# MAGIC interpretable, so the app recomputes LIVE as a slider moves and shows the exact per-driver
# MAGIC contribution. Position drivers: **GK** clean-sheet%/save%/aerial claims · **DEF**
# MAGIC tackles+int/aerial-duel%/progressive passes · **MF** progressive passes/chance creation/
# MAGIC ball recoveries · **FW** goals/xG/shot conversion/pressures · universal age/minutes/
# MAGIC contract/league strength.
# MAGIC
# MAGIC Deliberately transparent (not fit): with position-specific drivers and n≈20, calibrated
# MAGIC coefficients tied to plausible market ranges give an honest, legible story. **Production
# MAGIC path:** AutoML/regression on historical transfer fees — one-swap of these coefficients,
# MAGIC no app change. Logged as an MLflow **pyfunc** (pure python, no sklearn) → registered to
# MAGIC Unity Catalog → served on a **serverless** endpoint (scale-to-zero).

# COMMAND ----------

# MAGIC %pip install mlflow --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, mlflow

CATALOG, SCHEMA = "acme_sports", "demo"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.acme_transfer_valuation"
ENDPOINT = "acme-transfer-valuation"

# ---- CANONICAL SPEC (must match app/server/transfer_spec.py) ----
UNIVERSAL = [
    ("age", "Age", "yrs", 16, 36, 24, -2.5, 0),
    ("minutes", "Minutes (season)", "min", 0, 3400, 2000, 0.006, 0),
    ("months_left", "Contract remaining", "mo", 6, 60, 36, 0.35, 0),
    ("league_str", "League strength", "idx", 50, 100, 80, 0.5, 0),
]
POSITION = {
    "GK": [("clean_sheet_pct", "Clean-sheet %", "%", 10, 70, 35, 0.7, 0),
           ("save_pct", "Save %", "%", 55, 90, 72, 1.2, 0),
           ("aerial_claims_p90", "Aerial claims /90", "/90", 0, 3.5, 1.2, 5.0, 1)],
    "DEF": [("tackles_int_p90", "Tackles+int. won /90", "/90", 1, 8, 4.0, 6.0, 1),
            ("aerial_duel_pct", "Aerial duel %", "%", 40, 85, 62, 0.6, 0),
            ("prog_passes_p90", "Progressive passes /90", "/90", 1, 12, 5.0, 3.5, 1)],
    "MF": [("prog_passes_p90", "Progressive passes /90", "/90", 2, 16, 7.0, 4.0, 1),
           ("chance_creation_p90", "Chance creation /90", "/90", 0, 6, 2.0, 12.0, 1),
           ("ball_recoveries_p90", "Ball recoveries /90", "/90", 2, 14, 7.0, 2.5, 1)],
    "FW": [("goals_p90", "Goals /90", "/90", 0, 1.0, 0.35, 60.0, 2),
           ("xg_p90", "xG /90", "/90", 0, 0.9, 0.35, 40.0, 2),
           ("shot_conv_pct", "Shot conversion %", "%", 5, 30, 15, 1.2, 0),
           ("pressures_p90", "Pressures /90", "/90", 5, 35, 18, 0.4, 1)],
}
BASE = {"GK": 30.0, "DEF": 55.0, "MF": 70.0, "FW": 78.0}
GROUP_LABEL = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}
CLAMP = (3.0, 250.0)
SPEC_BLOB = {"universal": UNIVERSAL, "position": POSITION, "base": BASE, "clamp": CLAMP}

# COMMAND ----------

class TransferModel(mlflow.pyfunc.PythonModel):
    """value = base + Σ coef·(x−ref), clamped; returns exact per-driver contributions."""
    def load_context(self, context):
        with open(context.artifacts["spec"]) as f:
            self.s = json.load(f)

    def _specs(self, group):
        return self.s["universal"] + self.s["position"].get(group, self.s["position"]["MF"])

    def _score(self, group, values):
        base = self.s["base"].get(group, self.s["base"]["MF"])
        contribs, total = [], base
        for key, label, unit, lo, hi, ref, coef, dec in self._specs(group):
            v = values.get(key)
            x = float(v if v is not None else ref)
            xeff = max(x, 19.0) if key == "age" else x
            c = coef * (xeff - ref)
            contribs.append({"key": key, "label": label, "unit": unit,
                             "value": round(x, dec), "contribution": round(c, 2)})
            total += c
        lo_c, hi_c = self.s["clamp"]
        total = max(lo_c, min(hi_c, total))
        drivers = sorted(contribs, key=lambda d: -abs(d["contribution"]))
        return {"group": group, "base": round(base, 2), "value": round(total, 2),
                "contributions": contribs,
                "top_drivers": [{"feature": d["key"], "label": d["label"],
                                 "contribution": d["contribution"]} for d in drivers]}

    def predict(self, context, model_input):
        recs = model_input.to_dict("records") if hasattr(model_input, "to_dict") else model_input
        out = []
        for r in recs:
            grp = r.get("group") or "MF"
            # KPI values arrive as a JSON string in `payload` (position-agnostic, no
            # per-column numeric schema to enforce). Back-compat: fall back to loose columns.
            payload = r.get("payload")
            if payload not in (None, ""):
                vals = json.loads(payload) if isinstance(payload, str) else dict(payload)
            else:
                vals = {k: r.get(k) for k in r if k not in ("group", "payload")}
            out.append(json.dumps(self._score(grp, vals)))
        return out

# COMMAND ----------

import pandas as pd
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import Schema, ColSpec

with open("/tmp/transfer_spec.json", "w") as f:
    json.dump(SPEC_BLOB, f)

# SIGNATURE FIX: the KPI columns differ per position group, and MLflow strictly enforces
# per-column numeric types (it refuses even int->double), so a typed-column signature 400s
# any request whose columns/dtypes don't match the single logged example — which is exactly
# why every DEF/MF/GK request used to fall back to local math. Instead the contract is
# position-agnostic: `group` + a JSON-string `payload` of KPI values. Two string columns,
# always satisfied, zero numeric enforcement — works for every group and every slider value.
input_schema = Schema([ColSpec("string", "group"), ColSpec("string", "payload")])
output_schema = Schema([ColSpec("string")])
sig = ModelSignature(inputs=input_schema, outputs=output_schema)

example = pd.DataFrame([{"group": "FW", "payload": json.dumps(
    {"age": 23, "minutes": 2380, "months_left": 30, "league_str": 85,
     "goals_p90": 0.55, "xg_p90": 0.5, "shot_conv_pct": 21, "pressures_p90": 23})}])

mlflow.set_registry_uri("databricks-uc")
with mlflow.start_run(run_name="acme_transfer_calibrated") as run:
    mlflow.log_dict(SPEC_BLOB, "spec.json")
    info = mlflow.pyfunc.log_model(
        artifact_path="model", python_model=TransferModel(),
        artifacts={"spec": "/tmp/transfer_spec.json"}, signature=sig,
        input_example=example, registered_model_name=MODEL_NAME,
        pip_requirements=["mlflow", "pandas"])
    run_id = run.info.run_id
print("logged:", info.model_uri)

from mlflow.tracking import MlflowClient
c = MlflowClient(registry_uri="databricks-uc")
ver = max(int(v.version) for v in c.search_model_versions(f"name='{MODEL_NAME}'"))
print("registered version:", ver)

# COMMAND ----------

# ---- Deploy to serverless Model Serving ----
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
w = WorkspaceClient()
served = ServedEntityInput(entity_name=MODEL_NAME, entity_version=str(ver),
                           scale_to_zero_enabled=True, workload_size="Small")
existing = [e.name for e in (w.serving_endpoints.list() or [])]
if ENDPOINT in existing:
    w.serving_endpoints.update_config(name=ENDPOINT, served_entities=[served])
    print("updated endpoint:", ENDPOINT)
else:
    w.serving_endpoints.create(name=ENDPOINT,
        config=EndpointCoreConfigInput(served_entities=[served]))
    print("created endpoint:", ENDPOINT)

# COMMAND ----------

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
    for _ in range(6):
        try:
            resp = w.serving_endpoints.query(name=ENDPOINT, dataframe_records=example.to_dict("records"))
            test = resp.predictions if hasattr(resp, "predictions") else resp.as_dict()
            break
        except Exception as ex:
            test = f"retry: {str(ex)[:80]}"
            time.sleep(15)

dbutils.notebook.exit(json.dumps({"ok": bool(ready), "endpoint": ENDPOINT,
    "model": MODEL_NAME, "version": ver, "test": test}, default=str))

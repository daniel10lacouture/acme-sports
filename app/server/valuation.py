"""L2 — What-if valuation model client.

Primary path: the serverless Model Serving endpoint `acme-valuation` (UC model
`acme_sports.demo.acme_valuation`), a calibrated OLS that returns a player's market
value (€M) plus additive per-feature contributions for explainability.

Resilience: if the endpoint is unreachable/cold, fall back to the SAME model evaluated
locally from the embedded coefficients (identical math), so the app never breaks. The
scenario-impact badge reflects which path served the numbers.
"""
import os, json, urllib.request
from server import dbx

ENDPOINT = os.environ.get("VALUATION_ENDPOINT", "acme-valuation")
FEATURES = ["gpr", "age", "minutes", "months_left"]

# Embedded fallback = the exact fitted OLS coefficients (see scripts/lakebase_l2_valuation.py).
# Populated from the training run so local scoring matches the served model.
COEF = {
    "features": FEATURES,
    "coef": {"gpr": 6.625769103392924, "age": -4.1626918253070695,
             "minutes": -0.0017549102411040744, "months_left": -0.3510625797106396},
    "mean": {"gpr": 82.4, "age": 23.15, "minutes": 1834.25, "months_left": 35.7},
    "base": 56.675,
    "r2": 0.8595337917827569,
}

_cache = {}          # player_id -> scored dict
_last_source = None  # 'acme-valuation' | 'local-fallback' | None


def _feat_row(p):
    return {f: float(p.get(f) or 0) for f in FEATURES}


def _local_score(row):
    m = COEF
    contribs, val = {}, m["base"]
    for f in m["features"]:
        c = round(m["coef"][f] * (float(row[f]) - m["mean"][f]), 2)
        contribs[f] = c
        val += c
    drivers = sorted(contribs.items(), key=lambda kv: -abs(kv[1]))
    return {"value": round(val, 2), "base": round(m["base"], 2), "contributions": contribs,
            "top_drivers": [{"feature": k, "contribution": v} for k, v in drivers]}


def _endpoint_score(rows):
    body = json.dumps({"dataframe_records": rows}).encode()
    url = f"{dbx._host()}/serving-endpoints/{ENDPOINT}/invocations"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {dbx._token()}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return d.get("predictions") or d


def prime(players):
    """Batch-score a list of player dicts once; cache by player_id. Sets the source."""
    global _last_source
    rows = [_feat_row(p) for p in players]
    ids = [p["player_id"] for p in players]
    try:
        preds = _endpoint_score(rows)
        _last_source = ENDPOINT
    except Exception as e:
        preds = [_local_score(r) for r in rows]
        _last_source = f"local-fallback ({str(e)[:40]})"
    for pid, pred in zip(ids, preds):
        _cache[pid] = pred
    return _last_source


def _score_one(p):
    pid = p.get("player_id")
    if pid in _cache:
        return _cache[pid]
    row = _feat_row(p)
    try:
        pred = _endpoint_score([row])[0]
        global _last_source
        _last_source = ENDPOINT
    except Exception:
        pred = _local_score(row)
    if pid:
        _cache[pid] = pred
    return pred


def value_of(p):
    return _score_one(p)["value"]


def explain(p):
    return _score_one(p)


def endpoint_status():
    return _last_source or "not-yet-called"

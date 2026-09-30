"""AI Transfer Assistant — interactive, position-specific, explainable valuation.

Serves the player's synthetic position KPIs (from `player_kpis`) as slider definitions,
and scores a set of KPI values into a market value (€M) + exact per-driver contributions.

Primary path: the serverless Model Serving endpoint `acme-transfer-valuation` (UC model
`acme_sports.demo.acme_transfer_valuation`). Resilience: if the endpoint is cold/
unreachable, fall back to the IDENTICAL calibrated math in `transfer_spec` (same coefficients
logged into the model), so the app never breaks and the numbers agree. The UI recomputes
locally on every slider drag for instant feedback and hits the endpoint on load / on demand.
"""
import os, json, urllib.request
from server import dbx, transfer_spec as T

ENDPOINT = os.environ.get("TRANSFER_ENDPOINT", "acme-transfer-valuation")
CAT, SCH = dbx.CATALOG, dbx.SCHEMA
_last_source = "not-yet-called"


def _endpoint_score(group, values):
    global _last_source
    # Position-agnostic contract: group + JSON-string payload of this group's KPI values.
    # Avoids MLflow per-column type enforcement (which rejected all non-FW groups).
    kpis = {k: values.get(k) for k in T.kpi_keys(group)}
    rec = {"group": group, "payload": json.dumps(kpis)}
    body = json.dumps({"dataframe_records": [rec]}).encode()
    url = f"{dbx._host()}/serving-endpoints/{ENDPOINT}/invocations"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {dbx._token()}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    preds = d.get("predictions") or d
    pred = preds[0] if isinstance(preds, list) else preds
    if isinstance(pred, str):
        pred = json.loads(pred)
    _last_source = ENDPOINT
    return pred


def score(group, values, use_endpoint=True):
    """Value + contributions. Tries Model Serving, falls back to identical local math."""
    global _last_source
    if use_endpoint:
        try:
            return _endpoint_score(group, values)
        except Exception as e:
            _last_source = f"local-fallback ({str(e)[:40]})"
    else:
        _last_source = "local"
    return T.score(group, values)


def _player_kpis(player_id):
    """Load stored synthetic KPIs; if absent, derive universal drivers from players."""
    pid = player_id.replace("'", "")
    rows = dbx.query(f"""SELECT k.position_group, k.kpis_json, p.name
      FROM {CAT}.{SCH}.player_kpis k JOIN {CAT}.{SCH}.players p USING(player_id)
      WHERE k.player_id='{pid}'""")
    if rows:
        r = rows[0]
        return r["name"], r["position_group"], json.loads(r["kpis_json"])
    pr = dbx.query(f"""SELECT name, positions, age, minutes, months_left
      FROM {CAT}.{SCH}.players WHERE player_id='{pid}'""")
    if not pr:
        return None, None, None
    p = pr[0]; grp = T.group_of(p["positions"])
    vals = {"age": p["age"], "minutes": p["minutes"], "months_left": p["months_left"], "league_str": 80}
    return p["name"], grp, vals


def schema(player_id):
    """Full payload for the assistant: sliders seeded to the player + initial valuation."""
    name, grp, vals = _player_kpis(player_id)
    if not grp:
        return None
    val = score(grp, vals, use_endpoint=True)
    return {"player_id": player_id, "name": name, "group": grp,
            "group_label": T.GROUP_LABEL.get(grp, grp),
            "sliders": T.slider_defs(grp, vals),
            "base": T.BASE.get(grp), "valuation": val, "source": _last_source}


def endpoint_status():
    return _last_source

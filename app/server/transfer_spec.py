"""Canonical, dependency-free spec + math for the AI Transfer Assistant valuation.

This is a **calibrated, illustrative** position-specific valuation model:
    value = position_base + Σ coef_k · (kpi_k − ref_k)      (clamped to a plausible range)
Every term is additive and interpretable, so the app can recompute the value LIVE as a
user drags a slider AND show the exact per-driver contribution. The SAME numbers are
logged into the MLflow pyfunc served on Model Serving (endpoint `acme-transfer-valuation`),
so the served model and the app's local fallback agree.

It is deliberately transparent (not fit on data): with position-specific drivers and n≈20
players, hand-calibrated coefficients tied to plausible market ranges give an honest, legible
story. The PRODUCTION path is AutoML/regression trained on historical transfer fees — a
one-swap of these coefficients, no app change. Nothing here imports 3rd-party packages, so it
runs identically in the Databricks App, in the model notebook, and in the local mock server.
"""

# ---- position grouping: primary position token -> driver group ----
POS_GROUP = {
    "GK": "GK",
    "CB": "DEF", "RB": "DEF", "LB": "DEF", "RWB": "DEF", "LWB": "DEF",
    "DM": "MF", "CM": "MF", "AM": "MF",
    "ST": "FW", "CF": "FW", "RW": "FW", "LW": "FW", "RM": "FW", "LM": "FW",
}
GROUP_LABEL = {"GK": "Goalkeeper", "DEF": "Defender", "MF": "Midfielder", "FW": "Forward"}


def group_of(positions):
    """Map a player's positions string ('RW, RM') to a driver group."""
    tok = str(positions or "").split(",")[0].strip().upper()
    return POS_GROUP.get(tok, "MF")


# ---- universal drivers (apply to every position) ----
# key: (label, unit, min, max, ref, coef €M/unit, decimals)
UNIVERSAL = [
    ("age",          "Age",               "yrs",  16,  36,  24,   -2.5, 0),
    ("minutes",      "Minutes (season)",  "min",   0, 3400, 2000, 0.006, 0),
    ("months_left",  "Contract remaining","mo",    6,  60,  36,   0.35, 0),
    ("league_str",   "League strength",   "idx",  50, 100,  80,   0.5,  0),
]

# ---- position-specific drivers ----
# same tuple shape as UNIVERSAL
POSITION = {
    "GK": [
        ("clean_sheet_pct",   "Clean-sheet %",      "%",    10, 70, 35,  0.7, 0),
        ("save_pct",          "Save %",             "%",    55, 90, 72,  1.2, 0),
        ("aerial_claims_p90", "Aerial claims /90",  "/90",   0, 3.5, 1.2, 5.0, 1),
    ],
    "DEF": [
        ("tackles_int_p90",   "Tackles+int. won /90","/90",  1,  8,  4.0, 6.0, 1),
        ("aerial_duel_pct",   "Aerial duel %",       "%",   40, 85, 62,  0.6, 0),
        ("prog_passes_p90",   "Progressive passes /90","/90",1, 12, 5.0, 3.5, 1),
    ],
    "MF": [
        ("prog_passes_p90",   "Progressive passes /90","/90",2, 16, 7.0, 4.0, 1),
        ("chance_creation_p90","Chance creation /90", "/90", 0,  6, 2.0,12.0, 1),
        ("ball_recoveries_p90","Ball recoveries /90", "/90", 2, 14, 7.0, 2.5, 1),
    ],
    "FW": [
        ("goals_p90",         "Goals /90",           "/90",  0, 1.0, 0.35,60.0, 2),
        ("xg_p90",            "xG /90",              "/90",  0, 0.9, 0.35,40.0, 2),
        ("shot_conv_pct",     "Shot conversion %",   "%",    5, 30, 15,  1.2, 0),
        ("pressures_p90",     "Pressures /90",       "/90",  5, 35, 18,  0.4, 1),
    ],
}

# base value (€M) of a reference player in each group (all drivers at ref)
BASE = {"GK": 30.0, "DEF": 55.0, "MF": 70.0, "FW": 78.0}
CLAMP = (3.0, 250.0)


def specs_for(group):
    """Ordered list of driver tuples for a group (universal first, then position)."""
    return UNIVERSAL + POSITION.get(group, POSITION["MF"])


def kpi_keys(group):
    return [s[0] for s in specs_for(group)]


def score(group, values):
    """value = base + Σ coef·(x−ref), clamped. Returns value + exact per-driver contributions."""
    base = BASE.get(group, BASE["MF"])
    contribs, total = [], base
    for key, label, unit, lo, hi, ref, coef, dec in specs_for(group):
        x = float(values.get(key, ref) if values.get(key) is not None else ref)
        # age: cap the youth premium below 19 (a 15yo doesn't out-value a 20yo on age alone)
        xeff = max(x, 19.0) if key == "age" else x
        c = coef * (xeff - ref)
        contribs.append({"key": key, "label": label, "unit": unit,
                         "value": round(x, dec), "contribution": round(c, 2)})
        total += c
    total = max(CLAMP[0], min(CLAMP[1], total))
    drivers = sorted(contribs, key=lambda d: -abs(d["contribution"]))
    return {"group": group, "group_label": GROUP_LABEL.get(group, group),
            "base": round(base, 2), "value": round(total, 2),
            "contributions": contribs,
            "top_drivers": [{"feature": d["key"], "label": d["label"],
                             "contribution": d["contribution"]} for d in drivers]}


def slider_defs(group, values):
    """Slider definitions for the UI, seeded with the player's current KPI values."""
    out = []
    for key, label, unit, lo, hi, ref, coef, dec in specs_for(group):
        v = values.get(key)
        v = round(float(v if v is not None else ref), dec)
        out.append({"key": key, "label": label, "unit": unit, "min": lo, "max": hi,
                    "ref": ref, "coef": coef, "decimals": dec, "value": v,
                    "universal": key in [u[0] for u in UNIVERSAL]})
    return out

#!/usr/bin/env python3
"""Dependency-free local preview: serves the SPA + replays captured API fixtures +
real clip images. Lets us render/screenshot the UI without Databricks OAuth.
Run: python3 mock/mock_server.py 8890   then open http://localhost:8890
"""
import json, os, sys, urllib.parse, hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from server import transfer_spec as T   # canonical transfer-valuation spec (pure python)
STATIC = os.path.join(ROOT, "app", "static")
FIX = os.path.join(ROOT, "mock", "fixtures")
CLIPS = os.path.join(ROOT, "data", "clips")
MANIFEST = {m["clip_id"]: m["file"] for m in json.load(open(os.path.join(CLIPS, "manifest.json")))}

# ---- Lakebase scenario preview (in-memory; mirrors server/impact.py math) ----
SQUAD = json.load(open(os.path.join(FIX, "squad.json")))
BY_ID = {p["player_id"]: p for p in SQUAD}


def _val(p):
    return float(_valuation(p)["value"])  # model-based value (mirrors L2 endpoint)


SCENARIOS = {
    "scn_a_alvarez": {"scenario_id": "scn_a_alvarez", "name": "Scenario A — Sign Álvarez, promote Dowman",
        "created_by": "Daniel Lacouture (app)", "created_at": "2026-08-19 15:40:00+00:00",
        "base_formation": "4-3-3", "notes": "Add a proven №9 and blood the academy gem.",
        "moves": [
            {"player_id": "p_alvarez", "action": "buy", "adjusted_wage": 12.0, "adjusted_value": 100.0, "note": "Marquee striker signing"},
            {"player_id": "p_dowman", "action": "promote", "adjusted_wage": 1.5, "adjusted_value": 8.0, "note": "Promote from academy"}]},
    "scn_b_saliba_dowman": {"scenario_id": "scn_b_saliba_dowman", "name": "Scenario B — Sell Saliba, promote Dowman",
        "created_by": "you@example.com", "created_at": "2026-08-19 16:22:45+00:00",
        "base_formation": "4-3-3", "notes": "What-if: fund the rebuild by selling Saliba; promote Dowman from the academy.",
        "moves": [
            {"player_id": "p_saliba", "action": "sell", "adjusted_wage": 0.0, "adjusted_value": 90.0, "note": "Sell at ~est valuation high to fund rebuild"},
            {"player_id": "p_dowman", "action": "promote", "adjusted_wage": 1.5, "adjusted_value": 8.0, "note": "Promote from academy to first team; wage bump 0.2 -> 1.5"}]},
    "scn_user_timber": {"scenario_id": "scn_user_timber", "name": "Sell Timber, buy Álvarez",
        "created_by": "Daniel Lacouture (app)", "created_at": "2026-08-21 12:00:00+00:00",
        "base_formation": "4-3-3", "notes": "User-created what-if — deletable.",
        "moves": [
            {"player_id": "p_timber", "action": "sell", "adjusted_wage": 0.0, "adjusted_value": 55.0, "note": "Proceeds fund a striker"},
            {"player_id": "p_alvarez", "action": "buy", "adjusted_wage": 12.0, "adjusted_value": 100.0, "note": "Marquee №9"}]},
}
# Seeded/demo scenarios — protected (mirrors server/lakebase.SEEDED_SCENARIOS).
SEEDED = {"scn_a_alvarez", "scn_b_saliba_dowman"}


def _apply(scen):
    value = sum(_val(p) for p in SQUAD)
    wage = sum(float(p.get("wage_per_yr") or 0) for p in SQUAD)
    n = len(SQUAD); cap = spend = proceeds = 0.0; lines = []
    for m in scen.get("moves", []):
        p = BY_ID.get(m["player_id"], {}); pname = p.get("name", m["player_id"])
        cv = _val(p); cw = float(p.get("wage_per_yr") or 0)
        av = float(m.get("adjusted_value") or 0); aw = float(m.get("adjusted_wage") or 0)
        act = m.get("action")
        if act == "sell":
            value -= cv; wage -= cw; proceeds += av; cap += av - cv; n -= 1
            lines.append({"player_id": m["player_id"], "name": pname, "action": act, "value_delta": round(-cv, 1), "wage_delta": round(-cw, 1), "capital_gain": round(av - cv, 1), "note": m.get("note")})
        elif act == "buy":
            value += av; wage += aw; spend += av; n += 1
            lines.append({"player_id": m["player_id"], "name": pname, "action": act, "value_delta": round(av, 1), "wage_delta": round(aw, 1), "capital_gain": 0.0, "note": m.get("note")})
        elif act == "promote":
            wage += aw - cw
            lines.append({"player_id": m["player_id"], "name": pname, "action": act, "value_delta": 0.0, "wage_delta": round(aw - cw, 1), "capital_gain": 0.0, "note": m.get("note")})
        else:
            lines.append({"player_id": m["player_id"], "name": pname, "action": "keep", "value_delta": 0.0, "wage_delta": 0.0, "capital_gain": 0.0, "note": m.get("note")})
    return {"squad_value": round(value, 1), "wage_bill": round(wage, 1), "capital_gains": round(cap, 1),
            "net_spend": round(spend - proceeds, 1), "n_players": n, "move_lines": lines}


def _compare():
    base = {"squad_value": round(sum(_val(p) for p in SQUAD), 1),
            "wage_bill": round(sum(float(p.get("wage_per_yr") or 0) for p in SQUAD), 1),
            "capital_gains": 0.0, "net_spend": 0.0, "n_players": len(SQUAD)}
    scs = []
    for s in SCENARIOS.values():
        agg = _apply(s)
        agg["deltas"] = {"squad_value": round(agg["squad_value"] - base["squad_value"], 1),
                         "wage_bill": round(agg["wage_bill"] - base["wage_bill"], 1),
                         "capital_gains": agg["capital_gains"], "net_spend": agg["net_spend"]}
        scs.append({"scenario_id": s["scenario_id"], "name": s["name"], "base_formation": s["base_formation"],
                    "notes": s["notes"], "moves": s["moves"], "seeded": s["scenario_id"] in SEEDED, **agg})
    return {"current": base, "scenarios": scs, "valuation_model": "acme-valuation (mock)"}


def _scen_list():
    return [{"scenario_id": s["scenario_id"], "name": s["name"], "created_by": s["created_by"],
             "created_at": s["created_at"], "base_formation": s["base_formation"], "notes": s["notes"],
             "seeded": s["scenario_id"] in SEEDED,
             "n_moves": len(s["moves"])} for s in SCENARIOS.values()]


# ---- L2 valuation (mirrors server/valuation.py COEF) ----
VAL_COEF = {"features": ["gpr", "age", "minutes", "months_left"],
    "coef": {"gpr": 6.625769103392924, "age": -4.1626918253070695,
             "minutes": -0.0017549102411040744, "months_left": -0.3510625797106396},
    "mean": {"gpr": 82.4, "age": 23.15, "minutes": 1834.25, "months_left": 35.7}, "base": 56.675}


def _valuation(p):
    m = VAL_COEF
    contribs, val = {}, m["base"]
    for f in m["features"]:
        c = round(m["coef"][f] * (float(p.get(f) or 0) - m["mean"][f]), 2)
        contribs[f] = c
        val += c
    drivers = sorted(contribs.items(), key=lambda kv: -abs(kv[1]))
    return {"value": round(val, 2), "base": round(m["base"], 2), "contributions": contribs,
            "top_drivers": [{"feature": k, "contribution": v} for k, v in drivers]}


# ---- AI Transfer Assistant (mirrors scripts/gen_player_kpis.py + server/transfer.py) ----
TF_LEAGUE = {"Arsenal": 85, "Manchester City": 88, "Real Madrid": 90, "Bayern Munich": 88,
             "Paris Saint-Germain": 80, "Crystal Palace": 82, "Aston Villa": 82,
             "AC Milan": 78, "Newcastle": 82, "Barcelona": 88}


def _tf_kpival(pid, q, lo, hi, ref, dec):
    if q >= 0.5:
        v = ref + (q - 0.5) / 0.5 * (hi - ref) * 0.92
    else:
        v = ref - (0.5 - q) / 0.5 * (ref - lo) * 0.92
    v += (_seed(pid, "j") - 0.5) * (hi - lo) * 0.08
    return round(max(lo, min(hi, v)), dec)


def _tf_kpis(p):
    pid = p["player_id"]; grp = T.group_of(p["positions"])
    q = max(0.0, min(1.0, (float(p["gpr"]) - 60) / 35.0))
    vals = {"age": int(p["age"]), "minutes": int(p["minutes"]),
            "months_left": int(p["months_left"]), "league_str": TF_LEAGUE.get(p["club"], 80)}
    for key, label, unit, lo, hi, ref, coef, dec in T.POSITION[grp]:
        vals[key] = _tf_kpival(pid, q, lo, hi, ref, dec)
    return grp, vals


def _tf_schema(pid):
    p = BY_ID.get(pid)
    if not p:
        return None
    grp, vals = _tf_kpis(p)
    val = T.score(grp, vals)
    return {"player_id": pid, "name": p["name"], "group": grp,
            "group_label": T.GROUP_LABEL.get(grp, grp), "sliders": T.slider_defs(grp, vals),
            "base": T.BASE.get(grp), "valuation": val, "source": "acme-transfer-valuation (mock)"}


# ---- AI Nutrition (mirrors server/nutrition.py; metrics from physio fixture) ----
def _nt_metrics(pid):
    pl = {p["player_id"]: p for p in json.loads(fixture("physio.json"))}.get(pid)
    if not pl:
        return None
    p = BY_ID.get(pid, {})
    dist = float(pl.get("distance_7d_km") or 0)
    base_kcal = 2400 + (float(p.get("gpr") or 75) - 75) * 8
    kcal = int(round((base_kcal + dist / 7.0 * 90) / 50.0) * 50)
    return {"player_id": pid, "player_name": pl.get("player_name"), "positions": pl.get("positions"),
            "age": pl.get("age"), "gpr": p.get("gpr"), "distance_7d_km": pl.get("distance_7d_km"),
            "match_minutes_7d": pl.get("match_minutes_7d"), "avg_sleep_7d": pl.get("avg_sleep_7d"),
            "avg_recovery_7d": pl.get("avg_recovery_7d"),
            "recommended_minutes_next": pl.get("recommended_minutes_next"), "load_flag": pl.get("load_flag"),
            "acwr": pl.get("acwr"), "est_daily_kcal": kcal,
            "est_carbs_g": int(round(float(pl.get("recommended_minutes_next") or 60) * 1.1 + dist * 3))}


def _nt_plan(pid, note):
    m = _nt_metrics(pid) or {}
    dist = float(m.get("distance_7d_km") or 0)
    protein = int(round(140 + (float(m.get("gpr") or 75) - 75) * 0.8))
    base = {"daily_kcal": m.get("est_daily_kcal", 3200), "carbs_g": m.get("est_carbs_g", 520),
            "protein_g": protein, "hydration_l": round(2.5 + dist / 7.0 * 0.03, 1),
            "pre_match": "High-GI carbs ~3h pre-kickoff (rice/oats), low fat & fibre.",
            "matchday": "Carb top-up 60–90 min pre-match; fluids + electrolytes at half-time.",
            "recovery": "20–40g protein + carbs within 30 min post-session; standard sleep routine."}
    hot = float(m.get("acwr") or 1) > 1.3
    adjs = [{"item": "Carbohydrate", "change": ("+40g" if hot else "hold"),
             "why": (f"workload spiking (ACWR {m.get('acwr')}) — top up glycogen" if hot else "load is controlled")},
            {"item": "Hydration", "change": "+500ml", "why": "high distance covered last 7 days"}]
    if note:
        adjs.append({"item": "Diet swap", "change": "apply voice-note context", "why": "reflects the player's note"})
    adjustments = {"adjusted_kcal": base["daily_kcal"] + (150 if hot else 0),
                   "adjusted_carbs_g": base["carbs_g"] + (40 if hot else 0),
                   "adjusted_protein_g": base["protein_g"], "adjustments": adjs,
                   "summary": (("Lean into carbs and hydration to support the acute load spike."
                                if hot else "Hold the baseline plan; minor hydration bump.")
                               + (" Voice-note context factored in." if note else ""))}
    return {"player_id": pid, "player_name": m.get("player_name"), "metrics": m, "baseline": base,
            "adjustments": adjustments, "raw": None, "used_voice_note": bool(note),
            "source": "ai_query · databricks-gpt-5-mini (mock)"}


# ---- AI Opposition Analyst (mirrors server/opposition.py + scripts/gen_opponents.py) ----
OPPONENTS = [
    {"opponent_id": "opp_mancity", "opponent": "Manchester City", "competition": "Premier League",
     "match_date": "2026-08-30", "venue": "Away", "formation": "4-1-4-1", "play_style": "Positional possession",
     "ppda": 9.1, "xg_for_p90": 2.15, "xg_against_p90": 0.82, "field_tilt_pct": 68, "high_press_pct": 41,
     "possession_pct": 63, "clip_q": "Rodri", "key": {"name": "Rodri", "pos": "DM", "threat": "Sets tempo; screens counters; progresses through lines"}},
    {"opponent_id": "opp_madrid", "opponent": "Real Madrid", "competition": "Champions League",
     "match_date": "2026-09-16", "venue": "Home", "formation": "4-3-1-2", "play_style": "Transition / individual quality",
     "ppda": 12.4, "xg_for_p90": 2.02, "xg_against_p90": 1.05, "field_tilt_pct": 55, "high_press_pct": 28,
     "possession_pct": 52, "clip_q": "Vinicius", "key": {"name": "Vinicius Jr", "pos": "LW", "threat": "Devastating 1v1 in transition down the left"}},
    {"opponent_id": "opp_bayern", "opponent": "Bayern Munich", "competition": "Champions League",
     "match_date": "2026-10-01", "venue": "Away", "formation": "4-2-3-1", "play_style": "High press / wide overloads",
     "ppda": 8.3, "xg_for_p90": 2.28, "xg_against_p90": 0.95, "field_tilt_pct": 64, "high_press_pct": 47,
     "possession_pct": 60, "clip_q": "Luis Diaz", "key": {"name": "Luis Diaz", "pos": "LW", "threat": "Relentless wide runner and counter-presser"}},
]
OPP_BY = {o["opponent_id"]: o for o in OPPONENTS}


def _op_report(oid):
    o = OPP_BY.get(oid)
    if not o:
        return None
    clip = json.loads(clip_fixture(o["clip_q"]))
    c0 = (clip.get("clips") or [{}])[0]
    cit = {"clip_id": c0.get("clip_id"), "player_name": c0.get("player_name") or c0.get("name"),
           "club": c0.get("club"), "caption": c0.get("caption"), "media_type": c0.get("media_type"),
           "score": c0.get("score")} if c0 else None
    brief = {
        "summary": f"{o['opponent']} play a {o['formation']} {o['play_style'].lower()} game (PPDA {o['ppda']}, "
                   f"{o['possession_pct']}% possession). They build patiently and hurt you in the wide channels.",
        "how_they_hurt_us": ["Positional rotations pull markers out of shape",
                             f"{o['key']['name']} progresses through the lines from deep", "Quick switches to the far-side overload"],
        "how_we_beat_them": ["Direct runs in behind their high line", "Press the goalkeeper's first pass",
                             "Defend narrow and anticipate the switch"],
        "set_piece": f"Set-piece xG is a genuine threat — mark zonally and screen the near post.",
        "key_battle": f"Danger man: {o['key']['name']} — our defensive mid must apply tight pressure and cut passing lanes.",
    }
    return {"opponent_id": oid, "opponent": o["opponent"], "competition": o["competition"],
            "match_date": o["match_date"], "venue": o["venue"], "formation": o["formation"],
            "play_style": o["play_style"], "metrics": o, "brief": brief, "raw": None,
            "citations": [{"name": o["key"]["name"], "pos": o["key"]["pos"], "threat": o["key"]["threat"], "clip": cit}],
            "source": "ai_query · databricks-gpt-5-mini (mock)"}


# ---- AI Contract & FFP/PSR agent (mirrors server/ffp.py) ----
FFP_REVENUE, FFP_LIMIT, FFP_AGENT, FFP_OPEX, FFP_PSR_LOSS = 320.0, 0.70, 0.08, 95.0, 125.0


def _ffp_econ():
    out = []
    for p in SQUAD:
        if p.get("tier") != "First Team":
            continue
        gpv = float(p.get("gpv") or 0); wage = float(p.get("wage_per_yr") or 0)
        rem = round(float(p.get("months_left") or 24) / 12.0, 1); yrs = 5.0
        fee = round(gpv * (0.55 + 0.30 * _seed(p["player_id"], "fee")), 1) if gpv > 0 else 0.0
        amort = round(fee / yrs, 2)
        out.append({"player_id": p["player_id"], "name": p["name"], "acquisition_fee": fee,
                    "contract_years": yrs, "remaining_years": rem, "annual_wage": wage,
                    "annual_amortization": amort, "residual_book_value": round(max(0, amort * rem), 1),
                    "annual_squad_cost": round(wage + amort, 2)})
    return sorted(out, key=lambda r: -r["annual_squad_cost"])


def _ffp_summary():
    econ = _ffp_econ()
    wage = round(sum(r["annual_wage"] for r in econ), 1)
    amort = round(sum(r["annual_amortization"] for r in econ), 1)
    agent = round(wage * FFP_AGENT, 1); squad = round(wage + amort + agent, 1)
    ratio = round(squad / FFP_REVENUE, 3); limit_cost = round(FFP_LIMIT * FFP_REVENUE, 1)
    pl = round(FFP_REVENUE - (squad + FFP_OPEX), 1); psr3 = round(pl * 3, 1)
    flags = []
    for r in econ:
        if r["remaining_years"] <= 1.5:
            flags.append({"player": r["name"], "type": "Expiring deal", "severity": "high" if r["remaining_years"] <= 1 else "medium",
                          "detail": f"{r['remaining_years']}y left — renew or sell to avoid a free-transfer loss."})
        if r["annual_wage"] >= 12:
            flags.append({"player": r["name"], "type": "Wage concentration", "severity": "medium",
                          "detail": f"€{r['annual_wage']:.0f}M/yr — top-band earner weighting the wage bill."})
        if r["residual_book_value"] >= 45:
            flags.append({"player": r["name"], "type": "High book value", "severity": "low",
                          "detail": f"€{r['residual_book_value']:.0f}M unamortized — a sale books a large swing."})
    order = {"high": 0, "medium": 1, "low": 2}
    flags = sorted(flags, key=lambda f: order[f["severity"]])[:8]
    return {"assumptions": {"revenue_eur_m": FFP_REVENUE, "uefa_limit_pct": FFP_LIMIT, "agent_fee_pct": FFP_AGENT,
                            "other_opex_eur_m": FFP_OPEX, "psr_allowable_loss_eur_m": FFP_PSR_LOSS},
            "wage_bill": wage, "amortization": amort, "agent_fees": agent, "squad_cost": squad,
            "squad_cost_ratio": ratio, "limit_cost": limit_cost, "investment_headroom": round(limit_cost - squad, 1),
            "annual_pl": pl, "psr_3yr_projection": psr3, "psr_headroom": round(FFP_PSR_LOSS + psr3, 1),
            "compliant": (limit_cost - squad) >= 0, "players": econ, "flags": flags}


def _ffp_scenarios():
    s = _ffp_summary(); rev, cap, sc = FFP_REVENUE, FFP_LIMIT, s["squad_cost"]

    def pack(rev_, sc_):
        lim = round(cap * rev_, 1)
        return {"revenue": round(rev_, 1), "squad_cost": round(sc_, 1), "ratio": round(sc_ / rev_, 3),
                "limit_cost": lim, "headroom": round(lim - sc_, 1),
                "annual_pl": round(rev_ - (sc_ + FFP_OPEX), 1)}
    UP, FX = 65.0, 1.17
    ucl = {"uplift_eur_m": UP, "with_ucl": pack(rev, sc), "without_ucl": pack(rev - UP, sc),
           "headroom_swing": round(pack(rev, sc)["headroom"] - pack(rev - UP, sc)["headroom"], 1)}
    fee, wage, years = 90.0, 12.0, 5
    aa = round(fee / years, 1); ag = round(wage * FFP_AGENT, 1); ac = round(aa + wage + ag, 1)
    signing = {"name": "Julián Álvarez (illustrative target)", "fee_eur_m": fee, "wage_eur_m": wage,
               "years": years, "added_amortization": aa, "added_agent": ag, "added_squad_cost": ac,
               "before": pack(rev, sc), "after": pack(rev, sc + ac)}
    wb, wa = 10, 50; web = round(wb * 52 / 1000.0 * FX, 2); wea = round(wa * 52 / 1000.0 * FX, 2)
    aw = round(wea - web, 2); rc = round(aw * (1 + FFP_AGENT), 2)
    renewal = {"player": "Max Dowman", "wk_before_gbp_k": wb, "wk_after_gbp_k": wa,
               "wage_before_eur_m": web, "wage_after_eur_m": wea, "added_wage_eur_m": aw,
               "added_squad_cost": rc, "before": pack(rev, sc), "after": pack(rev, sc + rc)}
    return {"assumptions": {"ucl_uplift_eur_m": UP, "gbp_eur": FX, "revenue_eur_m": rev, "uefa_limit_pct": cap},
            "base": pack(rev, sc), "ucl": ucl, "signing": signing, "renewal": renewal}


def _ffp_brief():
    s = _ffp_summary(); pct = round(s["squad_cost_ratio"] * 100)
    verdict = "Compliant" if pct <= 60 else "Watch" if pct <= 70 else "At risk"
    brief = {"verdict": verdict,
             "headline": f"Squad-cost ratio {pct}% with €{s['investment_headroom']}M of investment headroom to the 70% cap.",
             "so_what": f"PSR 3-year headroom is €{s['psr_headroom']}M, so the constraint is the UEFA squad-cost ratio, not PSR. "
                        f"A marquee signing adds wages and amortization that erode the €{s['investment_headroom']}M room quickly.",
             "recommendation": "Fund any incoming fee by first resolving the expiring deals — renew or sell to protect ratio headroom."}
    ev = [{"player_name": p["name"], "file_uri": f"/Volumes/.../contract_{p['player_id'].split('_')[1]}.pdf",
           "ai_summary": f"{p['name']} — release clause and contract end parsed from the governed PDF via ai_parse_document; wage and term feed the amortization model."}
          for p in s["players"][:3]]
    return {"summary": s, "brief": brief, "raw": None, "evidence": ev, "source": "ai_query · databricks-gpt-5-mini (mock)"}


# ---- L3 injury & load-risk (mirrors scripts/lakebase_l3_injury.py) ----
IW = {"intercept": 18.0, "age_over_27": 2.6, "load_over_200": 0.10, "density_over_2": 5.0,
      "prior_injuries": 7.5, "accel_over_35": 0.9, "sprints_over_20": 0.8}


def _seed(pid, salt):
    return int(hashlib.md5(f"{pid}:{salt}".encode()).hexdigest(), 16) % 1000 / 1000.0


def _gps_mock(st, pid):
    """Synthetic STATSports GPS-vest summary for local preview (mirrors statsports_metrics)."""
    r = lambda salt: _seed(pid, salt)
    dist = int(9500 + r("d") * 3200)
    hsr = int(dist * (0.09 + r("h") * 0.04))
    sc = max(1, int(hsr / 24))
    ac = int(24 + r("ac") * 40); dc = int(20 + r("dc") * 40)
    pl = round(dist / 100.0 + hsr / 26 * 1.5 + (20 + r("pl") * 40) * 0.3, 1)
    return {"player_id": pid, "player_name": st.get("player_name"),
            "last_match_minutes": int(60 + r("lm") * 30), "season_avg_minutes": int(72 + r("m") * 18),
            "total_season_minutes": int(700 + r("t") * 500), "season_matches": 8,
            "total_distance_m": dist, "hsr_distance_m": hsr, "sprint_distance_m": sc * 22, "sprint_count": sc,
            "accel_count": ac, "decel_count": dc, "player_load": pl,
            "dynamic_stress_load": int(pl * 2.4 + ac * 0.5 + dc * 0.5),
            "hml_distance_m": int(hsr * 1.35 + dist * 0.04), "top_speed_kmh": round(30.5 + r("s") * 5, 1),
            "strain_delta_pct": round((r("sd") - 0.5) * 40, 1),
            "load_rank": 1 + int(r("rk") * 19), "squad_n": 20, "load_percentile": int(r("pc") * 100)}


def _injury_row(p):
    pid, age, mins = p["player_id"], int(p["age"]), int(p.get("minutes") or 0)
    load = int(min(360, mins / 34 * 4 * (0.75 + 0.5 * _seed(pid, "load"))))
    spr = round(14 + 12 * _seed(pid, "spr"), 1)
    acc = round(28 + 22 * _seed(pid, "acc"), 1)
    den = int(2 + round(2 * _seed(pid, "den")))
    prior = int(round(3 * _seed(pid, "hist") + (1 if age >= 30 else 0)))
    c = {"age": IW["age_over_27"] * max(0, age - 27), "recent load": IW["load_over_200"] * max(0, load - 200),
         "match density": IW["density_over_2"] * max(0, den - 2), "injury history": IW["prior_injuries"] * prior,
         "high accelerations": IW["accel_over_35"] * max(0, acc - 35), "sprint volume": IW["sprints_over_20"] * max(0, spr - 20)}
    score = max(3, min(95, IW["intercept"] + sum(c.values())))
    band = "High" if score >= 72 else "Elevated" if score >= 55 else "Moderate" if score >= 38 else "Low"
    avail = "Doubtful" if band == "High" else "Monitor" if band == "Elevated" else "Available"
    top = sorted(c.items(), key=lambda kv: -kv[1])[0][0]
    note = {"High": f"Manage load — {top} elevated; consider rotation.",
            "Elevated": f"Monitor {top}; limit high-intensity exposure.",
            "Moderate": "Within normal range; routine monitoring.",
            "Low": "Low load-risk; fully available."}[band]
    return {"player_id": pid, "name": p["name"], "tier": p.get("tier"), "risk_score": round(score, 1),
            "risk_band": band, "availability": avail, "top_factor": top, "risk_note": note,
            "recent_minutes_load": load, "sprints_per90": spr, "high_accel_per90": acc,
            "match_density_14d": den, "prior_injuries": prior,
            "contributions_json": json.dumps({k: round(v, 1) for k, v in c.items()})}


INJURY = sorted([_injury_row(p) for p in SQUAD], key=lambda r: -r["risk_score"])
INJURY_BY = {r["player_id"]: r for r in INJURY}

ASK_ANSWER = ("## Vitor Roque — Valuation & Scout Assessment\n\n"
  "**Vitor Roque's estimated valuation is €25–40M** (GPV €32M) with a **€60M release clause**.\\[[1]"
  "(https://x/genie/rooms/x/chats/x?gra_focus=1)\\] Our scout **Marco Bianchi** rates him a "
  "**Priority target** — explosive penalty-box striker, relentless press — recommending we move early."
  "\\[[2](https://x/explore/data/volumes/acme_sports/demo/documents?filePreviewPath=scout_note_roque.txt)\\]")


def fixture(name):
    p = os.path.join(FIX, name)
    return open(p, "rb").read() if os.path.exists(p) else b"{}"


def clip_fixture(q):
    ql = q.lower()
    if "vini" in ql or "vinic" in ql:
        return fixture("clip_vini_jr.json")
    if "luis" in ql or "diaz" in ql or "díaz" in ql:
        return fixture("clip_luis_diaz.json")
    if "rodri" in ql:
        return fixture("clip_rodri.json")
    if "red" in ql:
        return fixture("clip_player_in_a_red_kit.json")
    return fixture("clip_goalkeeper.json")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, str): body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if "/api/physio/" in self.path and self.path.endswith("/recommend"):
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            pid = self.path.split("/")[3]
            pl = {p["player_id"]: p for p in json.loads(fixture("physio.json"))}.get(pid, {})
            note = (body.get("note") or "").strip()
            rec = (f"Cap {pl.get('player_name','the player')} at {pl.get('recommended_minutes_next',60)} minutes next "
                   f"fixture — ACWR {pl.get('acwr','')}, GPS strain and 7-day recovery {pl.get('avg_recovery_7d','')}% "
                   f"are the drivers." + (f" Physio team note folded in: {note}" if note else ""))
            return self._send(200, json.dumps({"player_id": pid, "player_name": pl.get("player_name"),
                "recommended_minutes_next": pl.get("recommended_minutes_next"), "load_flag": pl.get("load_flag"),
                "acwr": pl.get("acwr"), "recommendation": rec, "used_team_note": bool(note),
                "source": "ai_query · databricks-gpt-5-mini (mock)"}))
        if "/api/nutrition/" in self.path and self.path.endswith("/recommend"):
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            pid = self.path.split("/")[3]
            self._send(200, json.dumps(_nt_plan(pid, body.get("note"))))
        elif self.path.startswith("/api/transfer/value"):
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            v = T.score(body.get("group", "MF"), body.get("values") or {})
            self._send(200, json.dumps({"valuation": v, "source": "acme-transfer-valuation (mock)"}))
        elif self.path.startswith("/api/ask"):
            self._send(200, json.dumps({"answer": ASK_ANSWER, "conversation_id": "mock"}))
        elif self.path.startswith("/api/scenario"):
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            sid = body.get("scenario_id") or ("scn_" + str(abs(hash(body.get("name", ""))))[:8])
            SCENARIOS[sid] = {"scenario_id": sid, "name": body.get("name", "Untitled"),
                "created_by": body.get("created_by", "app"), "created_at": "2026-08-19 17:00:00+00:00",
                "base_formation": body.get("base_formation", "4-3-3"), "notes": body.get("notes", ""),
                "moves": body.get("moves", [])}
            self._send(200, json.dumps(SCENARIOS[sid]))
        else:
            self._send(404, "{}")

    def do_DELETE(self):
        if self.path.startswith("/api/scenario/"):
            sid = self.path.rsplit("/", 1)[-1]
            if sid in SEEDED:
                return self._send(403, json.dumps({"detail": "seeded scenario is protected and cannot be deleted"}))
            if sid not in SCENARIOS:
                return self._send(404, json.dumps({"detail": "scenario not found"}))
            moves = len(SCENARIOS[sid].get("moves", []))
            del SCENARIOS[sid]
            return self._send(200, json.dumps({"found": True, "scenario_id": sid,
                                                "scenarios_deleted": 1, "moves_deleted": moves}))
        self._send(404, "{}")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path, qs = u.path, urllib.parse.parse_qs(u.query)
        if path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(STATIC, "index.html"), "rb").read(), "text/html")
        if path.startswith("/static/"):
            f = os.path.join(STATIC, path[len("/static/"):])
            if os.path.exists(f):
                ct = ("text/css" if f.endswith(".css") else "application/javascript" if f.endswith(".js")
                      else "image/png" if f.endswith(".png")
                      else "image/jpeg" if f.endswith((".jpg", ".jpeg")) else "text/plain")
                return self._send(200, open(f, "rb").read(), ct)
            return self._send(404, "not found", "text/plain")
        if path == "/api/scenarios": return self._send(200, json.dumps(_scen_list()))
        if path == "/api/scenarios/compare": return self._send(200, json.dumps(_compare()))
        if path.startswith("/api/scenario/"):
            sid = path.rsplit("/", 1)[-1]
            return self._send(200, json.dumps(SCENARIOS.get(sid, {})))
        if path.startswith("/api/transfer/"):
            pid = path.rsplit("/", 1)[-1]
            s = _tf_schema(pid)
            return self._send(200, json.dumps(s) if s else "{}")
        if path.startswith("/api/nutrition/"):
            pid = path.rsplit("/", 1)[-1]
            m = _nt_metrics(pid)
            return self._send(200, json.dumps(m) if m else "{}")
        if path == "/api/opposition": return self._send(200, json.dumps(
            [{k: o[k] for k in ("opponent_id","opponent","competition","match_date","venue","formation",
              "play_style","ppda","xg_for_p90","xg_against_p90","field_tilt_pct","high_press_pct","possession_pct")}
             for o in OPPONENTS]))
        if path.startswith("/api/opposition/") and path.endswith("/report"):
            oid = path.split("/")[3]
            r = _op_report(oid)
            return self._send(200, json.dumps(r) if r else "{}")
        if path == "/api/ffp": return self._send(200, json.dumps(_ffp_summary()))
        if path == "/api/ffp/brief": return self._send(200, json.dumps(_ffp_brief()))
        if path == "/api/ffp/scenarios": return self._send(200, json.dumps(_ffp_scenarios()))
        if path == "/api/injury": return self._send(200, json.dumps(INJURY))
        if path == "/api/physio": return self._send(200, fixture("physio.json"))
        if path.startswith("/api/physio/") and path.endswith("/recommend"):
            pid = path.split("/")[3]
            pl = {p["player_id"]: p for p in json.loads(fixture("physio.json"))}.get(pid, {})
            rec = (f"Cap {pl.get('player_name','the player')} at {pl.get('recommended_minutes_next',60)} minutes next fixture — "
                   f"ACWR {pl.get('acwr','')} with 7-day recovery {pl.get('avg_recovery_7d','')}% is the key driver. "
                   f"{'Workload is spiking above the 4-week norm; manage minutes to normalise acute:chronic load.' if pl.get('acwr',0)>1.3 else 'Recovery and injury markers support a controlled load.'}")
            return self._send(200, json.dumps({"player_id": pid, "player_name": pl.get("player_name"),
                "recommended_minutes_next": pl.get("recommended_minutes_next"), "load_flag": pl.get("load_flag"),
                "acwr": pl.get("acwr"), "recommendation": rec, "source": "ai_query · databricks-gpt-5-mini (mock)"}))
        if path.startswith("/api/physio/"):
            pid = path.rsplit("/", 1)[-1]
            f = f"physio_{pid}.json"
            raw = fixture(f) if os.path.exists(os.path.join(FIX, f)) else fixture("physio_p_saka.json")
            d = json.loads(raw); d["gps_metrics"] = _gps_mock(d.get("status", {}), pid)
            return self._send(200, json.dumps(d))
        if path.startswith("/api/valuation/"):
            pid = path.rsplit("/", 1)[-1]
            p = BY_ID.get(pid, {})
            return self._send(200, json.dumps({"player_id": pid, "name": p.get("name"),
                "gpv": p.get("gpv"), "valuation": _valuation(p), "source": "acme-valuation (mock)"}))
        if path == "/api/squad": return self._send(200, fixture("squad.json"))
        if path == "/api/summary": return self._send(200, fixture("summary.json"))
        if path == "/api/scouting": return self._send(200, fixture("scouting.json"))
        if path == "/api/documents": return self._send(200, fixture("documents.json"))
        if path == "/api/health": return self._send(200, json.dumps({"ok": True}))
        if path.startswith("/api/player/"):
            pid = path.rsplit("/", 1)[-1]
            f = f"player_{pid}.json"
            return self._send(200, fixture(f) if os.path.exists(os.path.join(FIX, f)) else fixture("player_p_saka.json"))
        if path == "/api/clip/search":
            return self._send(200, clip_fixture((qs.get("q") or [""])[0]))
        if path.startswith("/api/clip/video/"):
            cid = path.rsplit("/", 1)[-1]
            mp4 = os.path.join(CLIPS, f"{cid}.mp4")
            if os.path.exists(mp4):
                return self._send(200, open(mp4, "rb").read(), "video/mp4")
            return self._send(404, "no video", "text/plain")
        if path.startswith("/api/clip/image/"):
            cid = path.rsplit("/", 1)[-1]
            fn = MANIFEST.get(cid)
            # video clips: serve the real sampled-frame poster {cid}.jpg
            if os.path.exists(os.path.join(CLIPS, f"{cid}.mp4")):
                fn = f"{cid}.jpg"
            if fn and os.path.exists(os.path.join(CLIPS, fn)):
                ct = "image/png" if fn.endswith(".png") else "image/jpeg"
                return self._send(200, open(os.path.join(CLIPS, fn), "rb").read(), ct)
            return self._send(404, "no image", "text/plain")
        return self._send(404, "{}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8890
    print(f"Mock preview at http://localhost:{port}")
    HTTPServer(("127.0.0.1", port), H).serve_forever()

"""Scenario impact + compare math for the Planning tab.

Transparent, explainable aggregation: baseline squad from the Delta `players` table,
then apply each scenario's moves (sell / buy / promote / keep). Squad value uses the
L2 what-if valuation model when available (valuation.value_of), else falls back to the
player's GPV. Capital gains = sale price minus the player's model/book value.
"""
from server import dbx, lakebase

try:
    from server import valuation
except Exception:  # valuation model optional; math still works on GPV
    valuation = None


def _squad():
    rows = dbx.query(f"""
      SELECT player_id, name, club, positions, tier, age, gpr, minutes,
             wage_per_yr, gpv, est_valuation_low, est_valuation_high, months_left
      FROM {dbx.CATALOG}.{dbx.SCHEMA}.players""")
    return {r["player_id"]: r for r in rows}


def _value_of(p):
    """Model value (€M) if the L2 endpoint is available, else GPV."""
    if valuation is not None:
        try:
            return float(valuation.value_of(p))
        except Exception:
            pass
    return float(p.get("gpv") or 0.0)


def _baseline(squad):
    value = sum(_value_of(p) for p in squad.values())
    wage = sum(float(p.get("wage_per_yr") or 0.0) for p in squad.values())
    return {"squad_value": round(value, 1), "wage_bill": round(wage, 1),
            "capital_gains": 0.0, "net_spend": 0.0, "n_players": len(squad)}


def _apply(scenario, squad):
    value = sum(_value_of(p) for p in squad.values())
    wage = sum(float(p.get("wage_per_yr") or 0.0) for p in squad.values())
    n = len(squad)
    cap_gains = 0.0
    spend = 0.0
    proceeds = 0.0
    lines = []
    for m in scenario.get("moves", []):
        pid = m["player_id"]
        p = squad.get(pid, {})
        pname = p.get("name", pid)
        cur_val = _value_of(p) if p else 0.0
        cur_wage = float(p.get("wage_per_yr") or 0.0)
        adj_val = float(m.get("adjusted_value") or 0.0)
        adj_wage = float(m.get("adjusted_wage") or 0.0)
        act = m.get("action")
        if act == "sell":
            value -= cur_val
            wage -= cur_wage
            proceeds += adj_val
            gain = adj_val - cur_val
            cap_gains += gain
            n -= 1
            lines.append({"player_id": pid, "name": pname, "action": act,
                          "value_delta": round(-cur_val, 1), "wage_delta": round(-cur_wage, 1),
                          "capital_gain": round(gain, 1), "note": m.get("note")})
        elif act == "buy":
            value += adj_val
            wage += adj_wage
            spend += adj_val
            n += 1
            lines.append({"player_id": pid, "name": pname, "action": act,
                          "value_delta": round(adj_val, 1), "wage_delta": round(adj_wage, 1),
                          "capital_gain": 0.0, "note": m.get("note")})
        elif act == "promote":
            wage += (adj_wage - cur_wage)
            lines.append({"player_id": pid, "name": pname, "action": act,
                          "value_delta": 0.0, "wage_delta": round(adj_wage - cur_wage, 1),
                          "capital_gain": 0.0, "note": m.get("note")})
        else:  # keep
            lines.append({"player_id": pid, "name": pname, "action": "keep",
                          "value_delta": 0.0, "wage_delta": 0.0, "capital_gain": 0.0,
                          "note": m.get("note")})
    return {"squad_value": round(value, 1), "wage_bill": round(wage, 1),
            "capital_gains": round(cap_gains, 1), "net_spend": round(spend - proceeds, 1),
            "n_players": n, "move_lines": lines}


def compare():
    squad = _squad()
    if valuation is not None:
        try:
            valuation.prime(list(squad.values()))  # one batched serving call
        except Exception:
            pass
    base = _baseline(squad)
    scenarios = []
    for s in lakebase.list_scenarios():
        full = lakebase.get_scenario(s["scenario_id"])
        agg = _apply(full, squad)
        agg["deltas"] = {
            "squad_value": round(agg["squad_value"] - base["squad_value"], 1),
            "wage_bill": round(agg["wage_bill"] - base["wage_bill"], 1),
            "capital_gains": round(agg["capital_gains"], 1),
            "net_spend": round(agg["net_spend"], 1),
        }
        scenarios.append({"scenario_id": full["scenario_id"], "name": full["name"],
                          "base_formation": full["base_formation"], "notes": full["notes"],
                          "moves": full["moves"], "seeded": lakebase.is_seeded(full["scenario_id"]),
                          **agg})
    return {"current": base, "scenarios": scenarios,
            "valuation_model": (valuation.endpoint_status() if valuation else "gpv-fallback")}


def _sql_str(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def _sql_num(v):
    try:
        return str(float(v))
    except (TypeError, ValueError):
        return "NULL"


def sync_to_delta(scenario_id):
    """Best-effort: mirror one scenario's impact + moves into the Delta tables the Acme
    Scout Genie space reads, so a scenario created in the app becomes answerable in Genie."""
    squad = _squad()
    if valuation is not None:
        try:
            valuation.prime(list(squad.values()))
        except Exception:
            pass
    full = lakebase.get_scenario(scenario_id)
    if not full:
        return
    agg = _apply(full, squad)
    base = _baseline(squad)
    sid = _sql_str(scenario_id)
    imp = f"{dbx.CATALOG}.{dbx.SCHEMA}.scenario_impact"
    mov = f"{dbx.CATALOG}.{dbx.SCHEMA}.scenario_moves"
    dbx.query(f"DELETE FROM {imp} WHERE scenario_id={sid}")
    dbx.query(f"""INSERT INTO {imp}
      (scenario_id, name, created_by, base_formation, notes, squad_value, wage_bill,
       capital_gains, net_spend, n_players, squad_value_delta, wage_bill_delta) VALUES (
      {sid}, {_sql_str(full['name'])}, {_sql_str(full.get('created_by'))},
      {_sql_str(full.get('base_formation'))}, {_sql_str(full.get('notes'))},
      {_sql_num(agg['squad_value'])}, {_sql_num(agg['wage_bill'])}, {_sql_num(agg['capital_gains'])},
      {_sql_num(agg['net_spend'])}, {agg['n_players']},
      {_sql_num(agg['squad_value'] - base['squad_value'])}, {_sql_num(agg['wage_bill'] - base['wage_bill'])})""")
    dbx.query(f"DELETE FROM {mov} WHERE scenario_id={sid}")
    for l in agg["move_lines"]:
        m = next((x for x in full["moves"] if x["player_id"] == l["player_id"]), {})
        dbx.query(f"""INSERT INTO {mov}
          (scenario_id, scenario_name, player_id, player_name, action, adjusted_wage,
           adjusted_value, value_delta, wage_delta, capital_gain, note) VALUES (
          {sid}, {_sql_str(full['name'])}, {_sql_str(l['player_id'])}, {_sql_str(l['name'])},
          {_sql_str(l['action'])}, {_sql_num(m.get('adjusted_wage'))}, {_sql_num(m.get('adjusted_value'))},
          {_sql_num(l['value_delta'])}, {_sql_num(l['wage_delta'])}, {_sql_num(l['capital_gain'])},
          {_sql_str(l.get('note'))})""")


def delete_from_delta(scenario_id):
    """Best-effort: remove a scenario's mirrored rows from the Genie-facing Delta tables,
    symmetric with sync_to_delta. Swallowed by the caller if the app SP lacks MODIFY on the
    demo schema (same known grant gap as the on-save mirror); the authoritative delete is the
    Lakebase Postgres transaction."""
    sid = _sql_str(scenario_id)
    dbx.query(f"DELETE FROM {dbx.CATALOG}.{dbx.SCHEMA}.scenario_moves WHERE scenario_id={sid}")
    dbx.query(f"DELETE FROM {dbx.CATALOG}.{dbx.SCHEMA}.scenario_impact WHERE scenario_id={sid}")

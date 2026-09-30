#!/usr/bin/env python3
"""Build the additive Delta table `acme_sports.demo.player_kpis` for the AI Transfer
Assistant: one row per player with position-specific KPIs (GK/DEF/MF/FW drivers) plus
universal drivers (age/minutes/contract months/league strength).

DATA HONESTY: these KPIs are **synthetic but schema-representative** — deterministically
seeded from the player's GPR + position so elite players carry elite underlying numbers.
The live connector is a one-config swap: point the same columns at an Opta/StatsBomb
season-stats feed (per-90 metrics land in the identical schema). Nothing else is touched;
this is a brand-new additive table.

Run locally: python3 scripts/gen_player_kpis.py
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from server import transfer_spec as T  # canonical ranges/refs (single source of truth)

# reuse the repo's warehouse statement runner
sys.path.insert(0, os.path.dirname(__file__))
import dbsql

CAT, SCH = "acme_sports", "demo"
TBL = f"{CAT}.{SCH}.player_kpis"

# per-club league-strength index (Premier League strong; illustrative)
LEAGUE = {"Arsenal": 85, "Manchester City": 88, "Real Madrid": 90, "Bayern Munich": 88,
          "Paris Saint-Germain": 80, "Crystal Palace": 82, "Aston Villa": 82,
          "AC Milan": 78, "Newcastle": 82, "Barcelona": 88}


def _seed(pid, salt):
    return int(hashlib.md5(f"{pid}:{salt}".encode()).hexdigest(), 16) % 1000 / 1000.0


def _kpi(pid, q, lo, hi, ref, dec):
    """Quality-scaled KPI value within [lo,hi]; q in [0,1], ref maps to q≈0.5."""
    if q >= 0.5:
        v = ref + (q - 0.5) / 0.5 * (hi - ref) * 0.92
    else:
        v = ref - (0.5 - q) / 0.5 * (ref - lo) * 0.92
    v += (_seed(pid, "j") - 0.5) * (hi - lo) * 0.08     # small deterministic jitter
    return round(max(lo, min(hi, v)), dec)


def main():
    players = dbsql.query_rows(
        f"SELECT player_id, name, club, positions, age, gpr, minutes, months_left FROM {CAT}.{SCH}.players")
    rows = []
    for p in players:
        pid = p["player_id"]
        grp = T.group_of(p["positions"])
        q = max(0.0, min(1.0, (float(p["gpr"]) - 60) / 35.0))
        vals = {
            "age": int(p["age"]), "minutes": int(p["minutes"]),
            "months_left": int(p["months_left"]),
            "league_str": LEAGUE.get(p["club"], 80),
        }
        for key, label, unit, lo, hi, ref, coef, dec in T.POSITION[grp]:
            vals[key] = _kpi(pid, q, lo, hi, ref, dec)
        val = T.score(grp, vals)["value"]
        rows.append({"player_id": pid, "name": p["name"], "position_group": grp,
                     "kpis_json": json.dumps(vals), "calibrated_value": val})

    dbsql.run(f"DROP TABLE IF EXISTS {TBL}")
    dbsql.run(f"""CREATE TABLE {TBL} (
        player_id STRING, name STRING, position_group STRING,
        kpis_json STRING, calibrated_value DOUBLE)
        COMMENT 'AI Transfer Assistant — synthetic position-specific KPIs (Opta/StatsBomb-shaped); live connector = one-config swap'""")
    for r in rows:
        # kpis_json is pure JSON (double-quoted, no single quotes) -> safe inside a '...' SQL literal
        dbsql.run(
            f"INSERT INTO {TBL} VALUES ('{r['player_id']}', "
            f"'{r['name'].replace(chr(39), chr(39)+chr(39))}', '{r['position_group']}', "
            f"'{r['kpis_json']}', {r['calibrated_value']})")
    print(f"player_kpis: wrote {len(rows)} rows")
    for r in sorted(rows, key=lambda x: -x["calibrated_value"])[:8]:
        print(f"  {r['name']:<22} {r['position_group']:<4} €{r['calibrated_value']:.1f}M")


if __name__ == "__main__":
    main()

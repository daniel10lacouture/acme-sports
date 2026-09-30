#!/usr/bin/env python3
"""Build the additive Delta table `acme_sports.demo.opponents` for the AI Opposition /
Match-Prep Analyst: upcoming opponents with **event + tracking-shaped** team metrics.

DATA HONESTY: these are **synthetic but provider-shaped** — the columns mirror what an
Opta / StatsBomb (event) + SkillCorner (tracking) feed delivers (xG for/against, PPDA,
field tilt, high-press share, set-piece xG, build-up style, pressing zones). The live
connector is a one-config swap into the same schema. Key players are chosen to line up with
the existing `clip_index` so the generated report can cite real scouting clips.
Brand-new additive table — nothing else touched.

Run: python3 scripts/gen_opponents.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import dbsql

CAT, SCH = "acme_sports", "demo"
TBL = f"{CAT}.{SCH}.opponents"

# key_players use names the clip resolver maps 1:1 (Rodri / Vinicius / Luis Diaz / Alvarez)
OPP = [
    {"opponent_id": "opp_mancity", "opponent": "Manchester City", "competition": "Premier League",
     "match_date": "2026-08-30", "venue": "Away", "formation": "4-1-4-1", "play_style": "Positional possession",
     "ppda": 9.1, "xg_for_p90": 2.15, "xg_against_p90": 0.82, "field_tilt_pct": 68, "high_press_pct": 41,
     "setpiece_xg_p90": 0.28, "build_up": "GK-short, split centre-backs, invert full-back",
     "possession_pct": 63, "directness_idx": 22,
     "key_players": [{"name": "Rodri", "clip_q": "Rodri", "pos": "DM", "threat": "Sets tempo; screens counters; progresses through lines"}],
     "threats": ["Positional rotations pull markers out of shape", "Rodri's deep progression unlocks the press",
                 "Overloads the far side then switches"],
     "weaknesses": ["High line exposed in transition", "Vulnerable to direct runs in behind the inverted full-back",
                    "Can be pressed on the goalkeeper's first pass"]},
    {"opponent_id": "opp_madrid", "opponent": "Real Madrid", "competition": "Champions League",
     "match_date": "2026-09-16", "venue": "Home", "formation": "4-3-1-2", "play_style": "Transition / individual quality",
     "ppda": 12.4, "xg_for_p90": 2.02, "xg_against_p90": 1.05, "field_tilt_pct": 55, "high_press_pct": 28,
     "setpiece_xg_p90": 0.22, "build_up": "Absorb then break; long diagonals to the winger",
     "possession_pct": 52, "directness_idx": 41,
     "key_players": [{"name": "Vinicius Jr", "clip_q": "Vinicius", "pos": "LW", "threat": "Devastating 1v1 in transition down the left"}],
     "threats": ["Lightning transitions after regains", "Vinicius isolates the full-back 1v1",
                 "Midfield runners arrive late into the box"],
     "weaknesses": ["Mid-block can be out-possessed", "Left-back leaves space when Vinicius stays high",
                    "Less compact when chasing the game"]},
    {"opponent_id": "opp_bayern", "opponent": "Bayern Munich", "competition": "Champions League",
     "match_date": "2026-10-01", "venue": "Away", "formation": "4-2-3-1", "play_style": "High press / wide overloads",
     "ppda": 8.3, "xg_for_p90": 2.28, "xg_against_p90": 0.95, "field_tilt_pct": 64, "high_press_pct": 47,
     "setpiece_xg_p90": 0.31, "build_up": "Aggressive counter-press, wing overloads, early crosses",
     "possession_pct": 60, "directness_idx": 30,
     "key_players": [{"name": "Luis Diaz", "clip_q": "Luis Diaz", "pos": "LW", "threat": "Relentless wide runner and counter-presser"}],
     "threats": ["Suffocating counter-press wins the ball high", "Wide overloads create early-cross chances",
                 "Set-piece xG among the highest in Europe"],
     "weaknesses": ["Space in behind when both full-backs push", "Second-ball structure after crosses",
                    "Can be beaten through the press with one line-break pass"]},
]


def main():
    dbsql.run(f"DROP TABLE IF EXISTS {TBL}")
    dbsql.run(f"""CREATE TABLE {TBL} (
        opponent_id STRING, opponent STRING, competition STRING, match_date STRING, venue STRING,
        formation STRING, play_style STRING, ppda DOUBLE, xg_for_p90 DOUBLE, xg_against_p90 DOUBLE,
        field_tilt_pct INT, high_press_pct INT, setpiece_xg_p90 DOUBLE, build_up STRING,
        possession_pct INT, directness_idx INT, key_players STRING, threats STRING, weaknesses STRING)
        COMMENT 'AI Opposition Analyst — synthetic Opta/StatsBomb/SkillCorner-shaped opponent metrics; live feed = one-config swap'""")
    q = lambda s: str(s).replace("'", "''")   # escape single quotes for SQL string literals
    for o in OPP:
        dbsql.run(
            f"INSERT INTO {TBL} VALUES ('{o['opponent_id']}', '{q(o['opponent'])}', '{q(o['competition'])}', "
            f"'{o['match_date']}', '{o['venue']}', '{o['formation']}', '{q(o['play_style'])}', {o['ppda']}, "
            f"{o['xg_for_p90']}, {o['xg_against_p90']}, {o['field_tilt_pct']}, {o['high_press_pct']}, "
            f"{o['setpiece_xg_p90']}, '{q(o['build_up'])}', {o['possession_pct']}, {o['directness_idx']}, "
            f"'{q(json.dumps(o['key_players']))}', '{q(json.dumps(o['threats']))}', '{q(json.dumps(o['weaknesses']))}')")
    print(f"opponents: wrote {len(OPP)} rows")
    for o in OPP:
        print(f"  {o['opponent']:<18} {o['formation']:<8} PPDA {o['ppda']}  xGf {o['xg_for_p90']}  key: {o['key_players'][0]['name']}")


if __name__ == "__main__":
    main()

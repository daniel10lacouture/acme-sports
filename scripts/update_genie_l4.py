#!/usr/bin/env python3
"""L4 — additively add the fused tables + instructions + sample questions to the
existing Acme Scout Genie space. Preserves the current 4 tables, the documents
volume, and existing instructions/questions (full-replacement API, so we GET, extend,
and PUT back)."""
import json, subprocess, os, uuid, sys

PROFILE = "YOUR_PROFILE"
SID = "YOUR_GENIE_SPACE_ID"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
NEW_TABLES = ["acme_sports.demo.injury_risk", "acme_sports.demo.player_valuation",
              "acme_sports.demo.scenario_impact", "acme_sports.demo.scenario_moves"]
NEW_INSTRUCTION = (
    "FUSED PLANNING CAPABILITIES (what-if scenarios, valuation, injury):\n"
    "- scenario_impact: one row per what-if squad plan (scenario) with squad_value, wage_bill, "
    "capital_gains, net_spend (all EUR millions) and *_delta vs the Current squad. "
    "To answer 'in Scenario B, what's our squad value', read squad_value where name ILIKE '%Scenario B%'.\n"
    "- scenario_moves: the per-player sell/buy/promote/keep moves behind each scenario, with value_delta, "
    "wage_delta and capital_gain.\n"
    "- player_valuation: the what-if valuation model's value per player (model_value, EUR M) and the single "
    "biggest driver (top_driver / top_contribution). GPR is usually the dominant driver.\n"
    "- injury_risk: load-risk model over physical/tracking data. risk_score (0-100), risk_band "
    "(Low/Moderate/Elevated/High), availability (Available/Monitor/Doubtful), top_factor and a risk_note. "
    "'High injury risk' = risk_band IN ('Elevated','High') or availability <> 'Available'. "
    "For a scenario+injury question, join scenario_moves.player_id to injury_risk.player_id.")
NEW_QUESTIONS = [
    "In Scenario B, what's our squad value and who's the highest injury risk?",
    "Which first-team players are highest injury and load risk right now?",
    "What does the valuation model value Bukayo Saka at, and what's the biggest driver?",
    "Compare Scenario B's squad value, wage bill and capital gains vs our current squad.",
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV, **kw)


def main():
    r = run(["databricks", "genie", "get-space", SID, "--include-serialized-space",
             "-p", PROFILE, "-o", "json"])
    if r.returncode != 0:
        print("GET failed:", r.stderr); sys.exit(1)
    full = json.loads(r.stdout)
    s = full["serialized_space"]
    s = json.loads(s) if isinstance(s, str) else s

    # additive: tables
    tables = s.setdefault("data_sources", {}).setdefault("tables", [])
    have = {t.get("identifier") for t in tables}
    for t in NEW_TABLES:
        if t not in have:
            tables.append({"identifier": t})
    tables.sort(key=lambda t: t.get("identifier", ""))  # API requires sorted identifiers
    s["data_sources"]["tables"] = tables

    # additive: merge into the single allowed text_instruction (append our block to its content)
    ti = s.setdefault("instructions", {}).setdefault("text_instructions", [])
    if not ti:
        ti.append({"id": uuid.uuid4().hex, "content": []})
    it0 = ti[0]
    content = it0.get("content")
    if isinstance(content, str):
        content = [content]
    content = content or []
    joined = "\n".join(content)
    if "FUSED PLANNING CAPABILITIES" not in joined:
        content = [joined + "\n\n" + NEW_INSTRUCTION] if joined else [NEW_INSTRUCTION]
    it0["content"] = content
    ti[:] = [it0]  # exactly one

    # additive: sample questions
    sq = s.setdefault("config", {}).setdefault("sample_questions", [])
    existing_q = {q for item in sq for q in (item.get("question") or [])}
    for q in NEW_QUESTIONS:
        if q not in existing_q:
            sq.append({"id": uuid.uuid4().hex, "question": [q]})

    ti.sort(key=lambda x: x.get("id", ""))       # API requires sorted ids
    sq.sort(key=lambda x: x.get("id", ""))
    serialized = json.dumps(s)
    print("tables now:", [t["identifier"] for t in tables])
    print("n_instructions:", len(ti), "n_questions:", len(sq))

    upd = run(["databricks", "genie", "update-space", SID,
               "--serialized-space", serialized, "-p", PROFILE, "-o", "json"])
    if upd.returncode != 0:
        print("UPDATE failed:\n", upd.stderr, upd.stdout); sys.exit(1)
    print("UPDATE ok")


if __name__ == "__main__":
    main()

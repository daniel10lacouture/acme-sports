"""AI Opposition / Match-Prep Analyst.

From synthetic, provider-shaped opponent metrics (`opponents`, Opta/StatsBomb/SkillCorner-
shaped) it auto-generates a next-opponent scouting report + tactical plan via `ai_query` (FM),
grounded in the numbers. Each key-player danger point is backed by a **clip citation** — the
same deterministic clip resolver used by Scouting Clip Search — so the report links straight to
scouting film. Opponent data is synthetic today; the event/tracking feed is a one-config swap.
"""
import json
from server import dbx

CAT, SCH = dbx.CATALOG, dbx.SCHEMA
OPP_ENDPOINT = "databricks-gpt-5-mini"


def _esc(s):
    return str(s).replace("'", "")


def list_opponents():
    rows = dbx.query(f"""
      SELECT opponent_id, opponent, competition, match_date, venue, formation, play_style,
             ppda, xg_for_p90, xg_against_p90, field_tilt_pct, high_press_pct, possession_pct
      FROM {CAT}.{SCH}.opponents ORDER BY match_date""")
    return rows


def _opponent(opponent_id):
    rows = dbx.query(f"SELECT * FROM {CAT}.{SCH}.opponents WHERE opponent_id='{_esc(opponent_id)}'")
    return rows[0] if rows else None


def _clip_citation(clip_q):
    """Resolve a key-player name to their top scouting clip (reuses the clip search)."""
    try:
        r = dbx.search_clips(clip_q, k=1)
        clips = r.get("clips") or []
        if not clips:
            return None
        c = clips[0]
        return {"clip_id": c["clip_id"], "player_name": c.get("player_name") or c.get("name"),
                "club": c.get("club"), "caption": c.get("caption"),
                "media_type": c.get("media_type"), "score": c.get("score")}
    except Exception:
        return None


def report(opponent_id):
    """LIVE ai_query scouting report + tactical plan grounded in the opponent metrics,
    with clip citations for the key players."""
    o = _opponent(opponent_id)
    if not o:
        return None
    key_players = json.loads(o.get("key_players") or "[]")
    threats = json.loads(o.get("threats") or "[]")
    weaknesses = json.loads(o.get("weaknesses") or "[]")

    facts = (
        f"Opponent: {o['opponent']} ({o['competition']}, {o['venue']}, {o['match_date']}). "
        f"Formation {o['formation']}, style: {o['play_style']}. "
        f"PPDA {o['ppda']} (lower = more aggressive press), possession {o['possession_pct']}%, "
        f"field tilt {o['field_tilt_pct']}%, high-press share {o['high_press_pct']}%, directness {o['directness_idx']}. "
        f"xG for/90 {o['xg_for_p90']}, xG against/90 {o['xg_against_p90']}, set-piece xG/90 {o['setpiece_xg_p90']}. "
        f"Build-up: {o['build_up']}. Danger men: {', '.join(k['name']+' ('+k['pos']+')' for k in key_players)}. "
        f"Known threats: {'; '.join(threats)}. Known weaknesses: {'; '.join(weaknesses)}."
    )
    prompt = (
        "You are Arsenal's opposition analyst preparing the squad for this fixture. Using ONLY these "
        "figures, produce a concise match-prep brief as STRICT JSON with keys: "
        "summary (2 sentences on how they play), "
        "how_they_hurt_us (array of 3 short bullet strings), "
        "how_we_beat_them (array of 3 short tactical-plan bullet strings, specific to their weaknesses), "
        "set_piece (one sentence), key_battle (one sentence naming the danger man and who must stop them). "
        "No text outside the JSON. Figures: " + facts
    )
    rows = dbx.query(f"SELECT ai_query('{OPP_ENDPOINT}', '{_esc(prompt)}') AS r")
    raw = rows[0]["r"] if rows else ""
    brief = _parse_json(raw)

    citations = []
    for k in key_players:
        cit = _clip_citation(k.get("clip_q") or k["name"])
        citations.append({"name": k["name"], "pos": k.get("pos"), "threat": k.get("threat"), "clip": cit})

    return {"opponent_id": o["opponent_id"], "opponent": o["opponent"], "competition": o["competition"],
            "match_date": o["match_date"], "venue": o["venue"], "formation": o["formation"],
            "play_style": o["play_style"],
            "metrics": {k: o[k] for k in ("ppda", "xg_for_p90", "xg_against_p90", "field_tilt_pct",
                                          "high_press_pct", "possession_pct", "setpiece_xg_p90", "directness_idx")},
            "brief": brief, "raw": None if brief else raw,
            "citations": citations, "source": f"ai_query · {OPP_ENDPOINT}"}


def _parse_json(raw):
    if not raw:
        return None
    s = raw.strip(); a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            return None
    return None

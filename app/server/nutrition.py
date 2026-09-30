"""AI Nutrition Assistant.

Reuses the physio load snapshot (distance, sleep, recovery, next-fixture load) + an optional
scout/player **voice note** (captured through the same voice pipeline as scout reports) to
generate a tailored fuelling / diet recommendation via `ai_query` (FM). The plan is grounded
in the player's own numbers, so it is specific rather than generic. Data is synthetic today;
the physio feed is a one-config swap (see physio.py / ingest_whoop.py).
"""
import json
from server import dbx

CAT, SCH = dbx.CATALOG, dbx.SCHEMA
NUTRITION_ENDPOINT = "databricks-gpt-5-mini"


def _esc(s):
    return str(s).replace("'", "")


def metrics(player_id):
    """Fuelling-relevant metrics for a player, from the load snapshot + squad row."""
    pid = _esc(player_id)
    rows = dbx.query(f"""
      SELECT ls.player_id, ls.player_name, ls.positions, ls.age, ls.gpr,
             ls.distance_7d_km, ls.match_minutes_7d, ls.avg_sleep_7d, ls.avg_recovery_7d,
             ls.recommended_minutes_next, ls.load_flag, ls.acwr
      FROM {CAT}.{SCH}.load_status ls WHERE ls.player_id='{pid}'""")
    if not rows:
        return None
    m = rows[0]
    # transparent daily-energy estimate (illustrative): base by body profile + training load.
    dist = float(m.get("distance_7d_km") or 0)
    base_kcal = 2400 + (float(m.get("gpr") or 75) - 75) * 8      # fitter athletes carry more mass/output
    load_kcal = dist / 7.0 * 90                                  # ~90 kcal per km/day averaged over the week
    m["est_daily_kcal"] = int(round((base_kcal + load_kcal) / 50.0) * 50)
    m["est_carbs_g"] = int(round(float(m.get("recommended_minutes_next") or 60) * 1.1 + dist * 3))
    return m


def baseline(m):
    """Each player's standing BASELINE fuelling plan — transparent, derived from their
    profile + typical training load (no AI). The AI then proposes ADJUSTMENTS vs this."""
    dist = float(m.get("distance_7d_km") or 0)
    protein = int(round(140 + (float(m.get("gpr") or 75) - 75) * 0.8))
    hyd = round(2.5 + dist / 7.0 * 0.03, 1)
    return {
        "daily_kcal": m["est_daily_kcal"], "carbs_g": m["est_carbs_g"], "protein_g": protein,
        "hydration_l": hyd,
        "pre_match": "High-GI carbs ~3h pre-kickoff (rice/oats), low fat & fibre.",
        "matchday": "Carb top-up 60–90 min pre-match; fluids + electrolytes at half-time.",
        "recovery": "20–40g protein + carbs within 30 min post-session; standard sleep routine.",
    }


def recommend(player_id, note=None):
    """LIVE ai_query that outputs ADJUSTMENTS to the player's baseline plan (what to change
    and why) — grounded in their metrics + optional voice note — not a plan from scratch."""
    m = metrics(player_id)
    if not m:
        return None
    base = baseline(m)
    facts = (
        f"Player: {m['player_name']} ({m['positions']}), age {m['age']}. "
        f"Distance covered last 7 days: {m['distance_7d_km']} km. "
        f"Match minutes last 7 days: {m['match_minutes_7d']}. "
        f"7-day average sleep: {m['avg_sleep_7d']}h. 7-day average recovery: {m['avg_recovery_7d']}%. "
        f"Recommended minutes next fixture: {m['recommended_minutes_next']}. Load flag: {m['load_flag']}. "
        f"Estimated daily energy need: ~{m['est_daily_kcal']} kcal."
    )
    base_txt = (
        f" BASELINE plan already in place: {base['daily_kcal']} kcal/day, {base['carbs_g']}g carbs, "
        f"{base['protein_g']}g protein, {base['hydration_l']}L hydration; pre-match: {base['pre_match']} "
        f"matchday: {base['matchday']} recovery: {base['recovery']}"
    )
    voice = f" The player/nutritionist left this voice note: \"{_esc(note)}\"." if note else ""
    prompt = (
        "You are the club's performance nutritionist. The player ALREADY has the baseline plan below. "
        "Using ONLY the figures (and the voice note if present), output the ADJUSTMENTS to make to that "
        "baseline for the next few days — what to change and why — NOT a plan from scratch. If little needs "
        "to change, say so with 1 adjustment. Respond as STRICT JSON with keys: adjusted_kcal (int), "
        "adjusted_carbs_g (int), adjusted_protein_g (int), adjustments (array of 1-4 objects "
        "{item, change, why} — 'change' a short delta like '+40g' or 'swap pasta for rice', 'why' one short "
        "clause grounded in the numbers/voice note), summary (one sentence). No text outside the JSON. "
        "Figures: " + facts + base_txt + voice
    )
    rows = dbx.query(f"SELECT ai_query('{NUTRITION_ENDPOINT}', '{_esc(prompt)}') AS r")
    raw = rows[0]["r"] if rows else ""
    adj = _parse_plan(raw)
    return {"player_id": m["player_id"], "player_name": m["player_name"],
            "metrics": m, "baseline": base, "adjustments": adj, "raw": None if adj else raw,
            "used_voice_note": bool(note), "source": f"ai_query · {NUTRITION_ENDPOINT}"}


def _parse_plan(raw):
    """Best-effort JSON extraction from the FM response."""
    if not raw:
        return None
    s = raw.strip()
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(s[a:b + 1])
        except Exception:
            return None
    return None

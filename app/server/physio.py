"""AI Physio / Load Manager.

Reads governed load data — STATSports-style GPS sessions + Whoop-style recovery —
and the fused `load_status` snapshot (ACWR, sleep, recovery, injury-risk) to advise
how many minutes each player should get in the next fixture. The per-player
recommendation is generated LIVE by ai_query over the player's own numbers, so it is
grounded, not scripted. Data is synthetic/representative today; the Whoop connector
(`notebooks/ingest_whoop.py`) swaps in live data with no code change.
"""
from server import dbx

CAT, SCH = dbx.CATALOG, dbx.SCHEMA
PHYSIO_ENDPOINT = "databricks-gpt-5-mini"


def _esc(s):
    return str(s).replace("'", "")


def load_status():
    """Squad-wide load snapshot, most-at-risk first."""
    return dbx.query(f"""
      SELECT player_id, player_name, positions, age, gpr, injury_band,
             match_minutes_7d, match_minutes_30d, distance_7d_km,
             acute_load_7d, chronic_load_wk, acwr, matches_last_4d,
             avg_sleep_7d, avg_recovery_7d, hrv_recent_ms,
             recommended_minutes_next, load_flag, rationale
      FROM {CAT}.{SCH}.load_status
      ORDER BY CASE load_flag WHEN 'Red' THEN 0 WHEN 'Amber' THEN 1 ELSE 2 END, acwr DESC""")


def _status_row(player_id):
    rows = dbx.query(f"""
      SELECT * FROM {CAT}.{SCH}.load_status WHERE player_id='{_esc(player_id)}'""")
    return rows[0] if rows else None


def player_detail(player_id):
    """Load_status row + last-14-day GPS and recovery trend series for the chart."""
    st = _status_row(player_id)
    if not st:
        return None
    sessions = dbx.query(f"""
      SELECT session_date, session_type, minutes, total_distance_m, hsr_distance_m,
             sprint_count, player_load, top_speed_kmh
      FROM {CAT}.{SCH}.statsports_sessions
      WHERE player_id='{_esc(player_id)}' AND datediff(current_date(), session_date) < 14
      ORDER BY session_date""")
    recovery = dbx.query(f"""
      SELECT metric_date, sleep_hours, sleep_performance_pct, recovery_pct, day_strain,
             hrv_ms, resting_hr
      FROM {CAT}.{SCH}.whoop_daily
      WHERE player_id='{_esc(player_id)}' AND datediff(current_date(), metric_date) < 14
      ORDER BY metric_date""")
    return {"status": st, "sessions": sessions, "recovery": recovery,
            "gps_metrics": _gps_metrics(player_id)}


def _gps_metrics(player_id):
    """STATSports GPS-vest per-player summary (latest match + season + peer rank)."""
    rows = dbx.query(f"""
      SELECT player_id, player_name, last_match_minutes, season_avg_minutes,
             total_season_minutes, season_matches, total_distance_m, hsr_distance_m,
             sprint_distance_m, sprint_count, accel_count, decel_count, player_load,
             dynamic_stress_load, hml_distance_m, top_speed_kmh, strain_delta_pct,
             load_rank, squad_n, load_percentile
      FROM {CAT}.{SCH}.statsports_metrics WHERE player_id='{_esc(player_id)}'""")
    return rows[0] if rows else None


def recommend(player_id, team_note=None):
    """LIVE ai_query recommendation grounded in the player's own load numbers AND, when
    provided, the physio team's own note (human-in-the-loop: it is weighted in the prompt)."""
    st = _status_row(player_id)
    if not st:
        return None
    m = _gps_metrics(player_id) or {}
    facts = (
        f"Player: {st['player_name']} ({st['positions']}), age {st['age']}. "
        f"Match minutes last 7 days: {st['match_minutes_7d']}, last 30 days: {st['match_minutes_30d']}. "
        f"Acute:chronic workload ratio (ACWR): {st['acwr']} (danger zone is >1.3). "
        f"7-day avg sleep: {st['avg_sleep_7d']}h, 7-day avg Whoop recovery: {st['avg_recovery_7d']}%, "
        f"recent HRV: {st['hrv_recent_ms']}ms. Injury-risk band: {st['injury_band']}. "
        f"Matches in the last 4 days: {st['matches_last_4d']}. "
        f"STATSports GPS last match: {m.get('total_distance_m')}m total distance, "
        f"{m.get('hsr_distance_m')}m high-speed running, Dynamic Stress Load {m.get('dynamic_stress_load')}, "
        f"match-over-match strain delta {m.get('strain_delta_pct')}%, cumulative-load rank "
        f"{m.get('load_rank')} of {m.get('squad_n')} ({m.get('load_percentile')}th percentile in the squad). "
        f"Model-recommended minutes for the next fixture: {st['recommended_minutes_next']}."
    )
    note = (team_note or "").strip()
    note_line = (f" Physio team note (hands-on clinical judgment from staff — weight this heavily "
                 f"and reflect it explicitly): \"{note}\".") if note else ""
    prompt = (
        "You are the club's AI physio / sports scientist. Using ONLY these figures and the physio "
        "team note if present, give the sporting director a 2-3 sentence recommendation on how to "
        "manage this player's minutes and rotation in the next fixture and why (name the key driver: "
        "workload spike, poor recovery/sleep, GPS strain, or injury risk). If a physio team note is "
        "present, it reflects staff judgment and must shape the recommendation. Be direct and "
        "practical. Figures: " + facts + note_line
    )
    rows = dbx.query(f"SELECT ai_query('{PHYSIO_ENDPOINT}', '{_esc(prompt)}') AS r")
    advice = rows[0]["r"] if rows else ""
    return {
        "player_id": st["player_id"], "player_name": st["player_name"],
        "recommended_minutes_next": st["recommended_minutes_next"],
        "load_flag": st["load_flag"], "acwr": st["acwr"],
        "recommendation": advice, "used_team_note": bool(note),
        "source": f"ai_query · {PHYSIO_ENDPOINT}",
    }

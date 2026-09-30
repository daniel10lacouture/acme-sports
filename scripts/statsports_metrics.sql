-- ============================================================================
-- WS5 — STATSports GPS-vest player-load metrics (ADDITIVE, synthetic).
-- Per-player summary derived from the existing statsports_sessions match rows +
-- a few STATSports-schema-representative derived metrics (sprint distance, Dynamic
-- Stress Load, high-metabolic-load distance), match-over-match strain delta, season
-- minutes, and cumulative-load rank/percentile vs team peers. New table only —
-- statsports_sessions / load_status / the 4 spine tables are untouched.
-- ============================================================================
CREATE OR REPLACE TABLE acme_sports.demo.statsports_metrics AS
WITH matches AS (
  SELECT s.*, row_number() OVER (PARTITION BY player_id ORDER BY session_date DESC) AS rn
  FROM acme_sports.demo.statsports_sessions s
  WHERE session_type = 'match' AND minutes > 0
),
latest AS (SELECT * FROM matches WHERE rn = 1),
prev   AS (SELECT player_id, player_load AS prev_player_load FROM matches WHERE rn = 2),
season AS (
  SELECT player_id,
         CAST(ROUND(AVG(minutes)) AS INT)  AS season_avg_minutes,
         CAST(SUM(minutes) AS INT)         AS total_season_minutes,
         COUNT(*)                          AS season_matches
  FROM matches GROUP BY player_id
),
derived AS (
  SELECT
    l.player_id, l.player_name, l.positions,
    l.minutes                                             AS last_match_minutes,
    s.season_avg_minutes, s.total_season_minutes, s.season_matches,
    l.total_distance_m,
    l.hsr_distance_m,
    CAST(l.sprint_count * 22 AS INT)                      AS sprint_distance_m,
    l.sprint_count,
    l.accel_count, l.decel_count,
    l.player_load,
    CAST(ROUND(l.player_load * 2.4 + l.accel_count * 0.5 + l.decel_count * 0.5) AS INT) AS dynamic_stress_load,
    CAST(ROUND(l.hsr_distance_m * 1.35 + l.total_distance_m * 0.04) AS INT)             AS hml_distance_m,
    l.top_speed_kmh,
    ROUND((l.player_load - p.prev_player_load) / NULLIF(p.prev_player_load, 0) * 100, 1) AS strain_delta_pct
  FROM latest l
  LEFT JOIN prev p   USING (player_id)
  LEFT JOIN season s USING (player_id)
)
SELECT
  *,
  CAST(RANK() OVER (ORDER BY dynamic_stress_load DESC) AS INT)                    AS load_rank,
  CAST(COUNT(*) OVER () AS INT)                                                   AS squad_n,
  CAST(ROUND(PERCENT_RANK() OVER (ORDER BY dynamic_stress_load) * 100) AS INT)    AS load_percentile
FROM derived;

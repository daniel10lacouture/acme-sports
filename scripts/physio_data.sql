-- ============================================================================
-- AI Physio / Load Manager — synthetic wearable + GPS data (ADDITIVE)
-- Schema-representative of STATSports (GPS/IMU) + Whoop (recovery/sleep/HRV).
-- Live connector is a config swap: Whoop API is reachable + OAuth-shaped; a
-- registered developer app + per-athlete token is all that's missing.
-- 20 players x 30 days. Working spine untouched.
-- ============================================================================

-- 1) STATSports APEX-style GPS sessions (one row per player per day).
CREATE OR REPLACE TABLE acme_sports.demo.statsports_sessions AS
WITH days AS (
  SELECT explode(sequence(date_add(current_date(), -29), current_date(), interval 1 day)) AS session_date
),
grid AS (
  SELECT p.player_id, p.name AS player_name, p.positions, p.age, p.gpr,
         d.session_date,
         datediff(current_date(), d.session_date) AS days_ago,
         pmod(datediff(d.session_date, DATE'2024-01-01') + abs(hash(p.player_id)), 4) AS md
  FROM acme_sports.demo.players p CROSS JOIN days d
),
mins AS (
  SELECT *,
    CASE WHEN md = 0 THEN 'match' ELSE 'training' END AS session_type,
    CASE
      WHEN md = 0 AND gpr >= 85 THEN LEAST(95, 70 + CAST(rand()*25 AS INT))
      WHEN md = 0 AND gpr >= 80 THEN 20 + CAST(rand()*55 AS INT)
      WHEN md = 0            THEN CAST(rand()*30 AS INT)
      ELSE 50 + CAST(rand()*25 AS INT)   -- training session duration
    END AS minutes
  FROM grid
),
dist AS (
  SELECT *,
    CAST(
      (CASE WHEN session_type = 'match'
            THEN minutes/90.0 * (9500 + rand()*2500)
            ELSE 4000 + rand()*3000 END)
      -- recent fixture-congestion spike (last 7 days) for a few players -> ACWR > 1.3,
      -- so the demo shows a load-driven flag even for an injury-Low player.
      * (CASE WHEN days_ago < 7 AND player_id IN ('p_saka','p_rice','p_saliba') THEN 1.55 ELSE 1.0 END)
    AS INT) AS total_distance_m
  FROM mins
)
SELECT
  player_id, player_name, positions, session_date, session_type, minutes,
  total_distance_m,
  CAST(total_distance_m * (0.09 + rand()*0.05) AS INT)        AS hsr_distance_m,   -- high-speed running
  CAST(total_distance_m * (0.09 + rand()*0.05) / 26 AS INT)   AS sprint_count,
  20 + CAST(rand()*45 AS INT)                                  AS accel_count,      -- >3 m/s^2
  18 + CAST(rand()*42 AS INT)                                  AS decel_count,
  ROUND(total_distance_m/100.0 + (total_distance_m*0.11/26)*1.5 + (20+rand()*45)*0.3, 1) AS player_load,
  ROUND(30.5 + rand()*5 - GREATEST(0, age-25)*0.12, 1)         AS top_speed_kmh
FROM dist;

-- 2) Whoop-style daily recovery/sleep/HRV (strain correlated with that day's GPS load).
CREATE OR REPLACE TABLE acme_sports.demo.whoop_daily AS
WITH s AS (
  SELECT ss.player_id, ss.player_name, ss.session_date AS metric_date, ss.session_type,
         ss.player_load, p.age
  FROM acme_sports.demo.statsports_sessions ss
  JOIN acme_sports.demo.players p ON p.player_id = ss.player_id
),
base AS (
  SELECT *,
    ROUND(LEAST(21, 6 + player_load/12.0 + rand()*3), 1) AS day_strain,
    ROUND(CASE WHEN session_type='match' THEN 6.0 + rand()*1.8 ELSE 6.8 + rand()*1.9 END, 1) AS sleep_hours
  FROM s
),
hrv AS (
  SELECT *,
    CAST(GREATEST(35, 92 - GREATEST(0, age-22)*2 + rand()*28 - day_strain*0.8) AS INT) AS hrv_ms,
    CAST(45 + GREATEST(0, age-22)*0.3 + rand()*9 AS INT) AS resting_hr
  FROM base
)
SELECT
  player_id, player_name, metric_date,
  sleep_hours,
  CAST(LEAST(100, sleep_hours/8.5*100 + rand()*8) AS INT) AS sleep_performance_pct,
  hrv_ms, resting_hr, day_strain,
  CAST(GREATEST(5, LEAST(99,
        40 + (sleep_hours-6)*12 + (hrv_ms-60)*0.4 - (day_strain-10)*2.2 + rand()*8)) AS INT) AS recovery_pct
FROM hrv;

-- 3) load_status — current snapshot per player: 7d/30d load, ACWR (acute:chronic
--    workload ratio), sleep/recovery, injury-risk fusion -> recommended minutes + flag.
CREATE OR REPLACE TABLE acme_sports.demo.load_status AS
WITH ss7 AS (
  SELECT player_id,
    SUM(CASE WHEN session_type='match' AND datediff(current_date(), session_date) < 7  THEN minutes ELSE 0 END) AS match_minutes_7d,
    SUM(CASE WHEN session_type='match' AND datediff(current_date(), session_date) < 30 THEN minutes ELSE 0 END) AS match_minutes_30d,
    ROUND(SUM(CASE WHEN datediff(current_date(), session_date) < 7  THEN total_distance_m ELSE 0 END)/1000.0, 1) AS distance_7d_km,
    ROUND(SUM(CASE WHEN datediff(current_date(), session_date) < 7  THEN player_load ELSE 0 END), 1) AS acute_load_7d,
    ROUND(SUM(CASE WHEN datediff(current_date(), session_date) < 28 THEN player_load ELSE 0 END)/4.0, 1) AS chronic_load_wk,
    SUM(CASE WHEN session_type='match' AND datediff(current_date(), session_date) < 4 THEN 1 ELSE 0 END) AS matches_last_4d
  FROM acme_sports.demo.statsports_sessions GROUP BY player_id
),
wd7 AS (
  SELECT player_id,
    ROUND(AVG(CASE WHEN datediff(current_date(), metric_date) < 7 THEN sleep_hours END), 1) AS avg_sleep_7d,
    CAST(AVG(CASE WHEN datediff(current_date(), metric_date) < 7 THEN recovery_pct END) AS INT) AS avg_recovery_7d,
    CAST(AVG(CASE WHEN datediff(current_date(), metric_date) < 3 THEN hrv_ms END) AS INT) AS hrv_recent_ms
  FROM acme_sports.demo.whoop_daily GROUP BY player_id
),
j AS (
  SELECT p.player_id, p.name AS player_name, p.positions, p.age, p.gpr, p.status,
         COALESCE(ir.risk_band, 'Low') AS injury_band,
         ss7.match_minutes_7d, ss7.match_minutes_30d, ss7.distance_7d_km,
         ss7.acute_load_7d, ss7.chronic_load_wk, ss7.matches_last_4d,
         ROUND(ss7.acute_load_7d / NULLIF(ss7.chronic_load_wk, 0), 2) AS acwr,
         wd7.avg_sleep_7d, wd7.avg_recovery_7d, wd7.hrv_recent_ms
  FROM acme_sports.demo.players p
  LEFT JOIN ss7 ON ss7.player_id = p.player_id
  LEFT JOIN wd7 ON wd7.player_id = p.player_id
  LEFT JOIN acme_sports.demo.injury_risk ir ON ir.player_id = p.player_id
),
rec AS (
  SELECT *,
    (CASE WHEN gpr>=85 THEN 90 WHEN gpr>=80 THEN 75 ELSE 45 END)
    - (CASE WHEN acwr > 1.5 THEN 35 WHEN acwr > 1.3 THEN 20 WHEN acwr < 0.8 THEN 10 ELSE 0 END)
    - (CASE WHEN avg_recovery_7d < 40 THEN 15 WHEN avg_recovery_7d < 55 THEN 8 ELSE 0 END)
    - (CASE WHEN avg_sleep_7d < 6.5 THEN 10 ELSE 0 END)
    - (CASE WHEN age > 30 THEN 5 ELSE 0 END)
    - (CASE WHEN injury_band = 'Elevated' THEN 15 WHEN injury_band = 'Moderate' THEN 8 ELSE 0 END)
    AS raw_rec
  FROM j
)
SELECT
  player_id, player_name, positions, age, gpr, injury_band,
  match_minutes_7d, match_minutes_30d, distance_7d_km,
  acute_load_7d, chronic_load_wk, acwr, matches_last_4d,
  avg_sleep_7d, avg_recovery_7d, hrv_recent_ms,
  CAST(ROUND(GREATEST(0, LEAST(90, raw_rec))/5.0)*5 AS INT) AS recommended_minutes_next,
  CASE
    WHEN acwr > 1.5 OR avg_recovery_7d < 40 OR injury_band = 'Elevated' THEN 'Red'
    WHEN acwr > 1.3 OR avg_recovery_7d < 55 OR avg_sleep_7d < 6.5 OR injury_band = 'Moderate' THEN 'Amber'
    ELSE 'Green'
  END AS load_flag,
  CONCAT_WS(' ',
    CONCAT('ACWR ', CAST(acwr AS STRING),
           CASE WHEN acwr > 1.3 THEN ' (spiking — acute load well above 4-week norm).'
                WHEN acwr < 0.8 THEN ' (undertrained — ease load up).'
                ELSE ' (balanced).' END),
    CONCAT('7d recovery ', CAST(avg_recovery_7d AS STRING), '%, sleep ', CAST(avg_sleep_7d AS STRING), 'h.'),
    CASE WHEN injury_band <> 'Low' THEN CONCAT('Injury risk ', injury_band, '.') ELSE '' END
  ) AS rationale
FROM rec;

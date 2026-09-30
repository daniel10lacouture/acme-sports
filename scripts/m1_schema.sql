-- ============ PLAYERS (20: first team + academy + targets) ============
CREATE TABLE IF NOT EXISTS acme_sports.demo.players (
  player_id STRING, name STRING, club STRING, positions STRING, age INT,
  nationality STRING, gpr INT, est_valuation_low DOUBLE, est_valuation_high DOUBLE,
  gpv DOUBLE, team_style_fit INT, player_style_fit INT, minutes INT,
  wage_per_yr DOUBLE, months_left INT, tier STRING, status STRING
) COMMENT 'Acme Sports player master — ratings, valuations, contract summary';

INSERT OVERWRITE acme_sports.demo.players VALUES
 -- First team (Arsenal)
 ('p_saka',    'Bukayo Saka',        'Arsenal',        'RW, RM',       23, 'England',     91, 130.0, 150.0, 140.0, 96, 95, 2380, 12.0, 30, 'First Team', 'Key Player'),
 ('p_rice',    'Declan Rice',        'Arsenal',        'DM, CM',       26, 'England',     90, 110.0, 130.0, 120.0, 95, 93, 2610, 14.0, 42, 'First Team', 'Key Player'),
 ('p_saliba',  'William Saliba',     'Arsenal',        'CB',           23, 'France',      89, 75.0,  90.0,  82.0,  94, 92, 2520, 9.5,  36, 'First Team', 'Key Player'),
 ('p_white',   'Ben White',          'Arsenal',        'RB, CB',       27, 'England',     84, 45.0,  55.0,  50.0,  88, 85, 1620, 8.0,  24, 'First Team', 'Rotation'),
 ('p_norgaard','Christian Norgaard', 'Arsenal',        'DM, CM',       31, 'Denmark',     78, 8.0,   12.0,  10.0,  80, 76, 1180, 4.0,  18, 'First Team', 'Squad Depth'),
 ('p_raya',    'David Raya',         'Arsenal',        'GK',           29, 'Spain',       87, 35.0,  45.0,  40.0,  90, 88, 2790, 7.5,  30, 'First Team', 'Key Player'),
 ('p_mosquera','Cristian Mosquera',  'Arsenal',        'CB, RB',       21, 'Spain',       80, 25.0,  35.0,  30.0,  84, 82, 640,  3.5,  48, 'First Team', 'Prospect'),
 ('p_odegaard','Martin Odegaard',    'Arsenal',        'AM, CM',       26, 'Norway',      88, 80.0,  95.0,  88.0,  93, 91, 2440, 11.0, 36, 'First Team', 'Captain'),
 ('p_gabriel', 'Gabriel Magalhaes',  'Arsenal',        'CB',           27, 'Brazil',      88, 65.0,  80.0,  72.0,  93, 90, 2680, 9.0,  30, 'First Team', 'Key Player'),
 ('p_timber',  'Jurrien Timber',     'Arsenal',        'RB, CB, LB',   23, 'Netherlands', 83, 40.0,  50.0,  45.0,  87, 84, 1980, 7.0,  36, 'First Team', 'Rotation'),
 -- Academy (Arsenal)
 ('p_dowman',  'Max Dowman',         'Arsenal',        'RW, AM',       15, 'England',     72, 5.0,   10.0,  8.0,   78, 80, 210,  0.20, 24, 'Academy',    'Prospect'),
 ('p_annous',  'Andre Annous',       'Arsenal',        'CM',           17, 'England',     68, 2.0,   5.0,   3.0,   74, 72, 90,   0.15, 36, 'Academy',    'Prospect'),
 ('p_clarke',  'Brayden Clarke',     'Arsenal',        'LB, LW',       16, 'England',     66, 1.0,   3.0,   2.0,   72, 70, 45,   0.12, 30, 'Academy',    'Prospect'),
 -- Scouting targets (other clubs)
 ('p_barcola', 'Bradley Barcola',    'Paris SG',       'LW, RW',       22, 'France',      85, 70.0,  90.0,  80.0,  89, 88, 2100, 8.0,  36, 'Target',     'Scouting'),
 ('p_olise',   'Michael Olise',      'Bayern Munich',  'RW, AM',       23, 'France',      88, 90.0,  110.0, 100.0, 92, 91, 2450, 10.0, 42, 'Target',     'Scouting'),
 ('p_roque',   'Vitor Roque',        'Palmeiras',      'ST',           20, 'Brazil',      79, 25.0,  40.0,  32.0,  83, 85, 1750, 4.5,  54, 'Target',     'Scouting'),
 ('p_alvarez', 'Julian Alvarez',     'Atletico Madrid','ST, AM',       25, 'Argentina',   89, 85.0,  100.0, 92.0,  91, 90, 2600, 12.0, 48, 'Target',     'Scouting'),
 ('p_rogers',  'Morgan Rogers',      'Aston Villa',    'AM, LW',       22, 'England',     82, 45.0,  60.0,  52.0,  86, 84, 2300, 6.0,  42, 'Target',     'Scouting'),
 ('p_brown',   'Nathaniel Brown',    'Eint. Frankfurt','LB',           22, 'Germany',     76, 18.0,  28.0,  22.0,  81, 79, 1900, 3.5,  36, 'Target',     'Scouting'),
 ('p_tonali',  'Sandro Tonali',      'Newcastle',      'DM, CM',       25, 'Italy',       85, 55.0,  70.0,  62.0,  88, 86, 2400, 9.0,  36, 'Target',     'Scouting');

-- ============ CONTRACTS (contract_end + release_clause filled from PDFs in M2) ============
CREATE TABLE IF NOT EXISTS acme_sports.demo.contracts (
  player_id STRING, contract_start DATE, contract_end DATE, wage_per_yr DOUBLE,
  release_clause DOUBLE, tier STRING, transfer_status STRING, last_updated DATE
) COMMENT 'Contract terms — contract dates and release_clause populated via ai_extract on contract PDFs';

INSERT OVERWRITE acme_sports.demo.contracts (player_id, contract_start, contract_end, wage_per_yr, release_clause, tier, transfer_status, last_updated) VALUES
 ('p_saka',    NULL, NULL, 12.0, NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_rice',    NULL, NULL, 14.0, NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_saliba',  NULL, NULL, 9.5,  NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_white',   NULL, NULL, 8.0,  NULL, 'First Team', 'Available',    DATE'2025-08-12'),
 ('p_norgaard',NULL, NULL, 4.0,  NULL, 'First Team', 'Available',    DATE'2025-08-12'),
 ('p_raya',    NULL, NULL, 7.5,  NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_mosquera',NULL, NULL, 3.5,  NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_odegaard',NULL, NULL, 11.0, NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_gabriel', NULL, NULL, 9.0,  NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 ('p_timber',  NULL, NULL, 7.0,  NULL, 'First Team', 'Not For Sale', DATE'2025-08-12'),
 -- targets: their current-club contracts (release clause is the transfer lever)
 ('p_roque',   NULL, NULL, 4.5,  NULL, 'Target', 'Monitoring', DATE'2025-08-12'),
 ('p_alvarez', NULL, NULL, 12.0, NULL, 'Target', 'Monitoring', DATE'2025-08-12'),
 ('p_olise',   NULL, NULL, 10.0, NULL, 'Target', 'Monitoring', DATE'2025-08-12'),
 ('p_tonali',  NULL, NULL, 9.0,  NULL, 'Target', 'Monitoring', DATE'2025-08-12');

-- ============ SCOUTING TARGETS ============
CREATE TABLE IF NOT EXISTS acme_sports.demo.scouting_targets (
  list_name STRING, player_id STRING, club STRING, positions STRING,
  country STRING, gpr INT, months_left INT
) COMMENT 'Curated scouting shortlists';

INSERT OVERWRITE acme_sports.demo.scouting_targets VALUES
 ('Summer 2026 — Wide Forwards',  'p_barcola', 'Paris SG',       'LW, RW', 'France',    85, 36),
 ('Summer 2026 — Wide Forwards',  'p_olise',   'Bayern Munich',  'RW, AM', 'France',    88, 42),
 ('Summer 2026 — Wide Forwards',  'p_rogers',  'Aston Villa',    'AM, LW', 'England',   82, 42),
 ('Summer 2026 — Striker Options','p_roque',   'Palmeiras',      'ST',     'Brazil',    79, 54),
 ('Summer 2026 — Striker Options','p_alvarez', 'Atletico Madrid','ST, AM', 'Argentina', 89, 48),
 ('Depth — Left Back',            'p_brown',   'Eint. Frankfurt','LB',     'Germany',   76, 36),
 ('Depth — Midfield',            'p_tonali',  'Newcastle',      'DM, CM', 'Italy',     85, 36);

-- ============ SCOUT REPORTS (one per transcript in the volume) ============
CREATE TABLE IF NOT EXISTS acme_sports.demo.scout_reports (
  player_id STRING, scout_name STRING, report_date DATE, status STRING, summary STRING
) COMMENT 'Structured scout report index; full text lives in documents volume transcripts';

INSERT OVERWRITE acme_sports.demo.scout_reports VALUES
 ('p_mosquera','Alejandro Ferreira', DATE'2025-08-10', 'Priority',   'Composed ball-playing CB, elite recovery pace, high system fit; priority buy-and-develop, wants one more viewing.'),
 ('p_roque',   'Marco Bianchi',      DATE'2025-07-28', 'Priority',   'Explosive penalty-box striker, relentless pressing; needs link-up refinement. Strong value at current clause.'),
 ('p_barcola', 'James Okafor',       DATE'2025-08-02', 'Active',     '1v1 wide threat with pace and end product; inconsistent decision-making. High ceiling, monitor price.'),
 ('p_olise',   'James Okafor',       DATE'2025-08-05', 'Priority',   'Elite creator from the right, set-piece value; injury history a flag. Top-tier fit, premium fee.'),
 ('p_alvarez', 'Marco Bianchi',      DATE'2025-07-30', 'Monitoring', 'Relentless, tactically intelligent forward; two-footed finisher. Expensive and well-protected contract.'),
 ('p_rogers',  'Priya Nair',         DATE'2025-08-08', 'Active',     'Powerful ball-carrier through the half-spaces; final-third efficiency improving. Good value, rising fee.'),
 ('p_brown',   'Tomasz Kowalski',    DATE'2025-08-06', 'Monitoring', 'Athletic modern LB, strong overlaps; defensively raw. Affordable depth option.'),
 ('p_tonali',  'Tomasz Kowalski',    DATE'2025-08-09', 'Active',     'Deep-lying orchestrator, excellent range of passing; needs consistent minutes. Fits our build-out.'),
 ('p_dowman',  'Priya Nair',         DATE'2025-08-11', 'Active',     'Generational academy talent, fearless dribbler; manage minutes. Long-term first-team projection.'),
 ('p_annous',  'Priya Nair',         DATE'2025-08-11', 'Monitoring', 'Technical central midfielder, calm under pressure; physically developing. Track over the season.');

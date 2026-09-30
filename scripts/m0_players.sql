CREATE TABLE IF NOT EXISTS acme_sports.demo.players (
  player_id STRING,
  name STRING,
  club STRING,
  positions STRING,
  age INT,
  nationality STRING,
  gpr INT,                    -- Acme Player Rating (0-100)
  est_valuation_low DOUBLE,   -- EUR millions
  est_valuation_high DOUBLE,  -- EUR millions
  gpv DOUBLE,                 -- Acme Player Value (EUR millions)
  team_style_fit INT,         -- 0-100
  player_style_fit INT,       -- 0-100
  minutes INT,                -- minutes played this season
  wage_per_yr DOUBLE,         -- EUR millions/yr
  months_left INT,            -- months left on contract
  tier STRING,
  status STRING
) COMMENT 'Acme Sports player master — ratings, valuations, contract summary';

INSERT OVERWRITE acme_sports.demo.players VALUES
 ('p_saka',    'Bukayo Saka',        'Arsenal', 'RW, RM',       23, 'England',     91, 130.0, 150.0, 140.0, 96, 95, 2380, 12.0, 30, 'First Team', 'Key Player'),
 ('p_rice',    'Declan Rice',        'Arsenal', 'DM, CM',       26, 'England',     90, 110.0, 130.0, 120.0, 95, 93, 2610, 14.0, 42, 'First Team', 'Key Player'),
 ('p_saliba',  'William Saliba',     'Arsenal', 'CB',           23, 'France',      89, 75.0,  90.0,  82.0,  94, 92, 2520, 9.5,  36, 'First Team', 'Key Player'),
 ('p_white',   'Ben White',          'Arsenal', 'RB, CB',       27, 'England',     84, 45.0,  55.0,  50.0,  88, 85, 1620, 8.0,  24, 'First Team', 'Rotation'),
 ('p_norgaard','Christian Norgaard', 'Arsenal', 'DM, CM',       31, 'Denmark',     78, 8.0,   12.0,  10.0,  80, 76, 1180, 4.0,  18, 'First Team', 'Squad Depth'),
 ('p_raya',    'David Raya',         'Arsenal', 'GK',           29, 'Spain',       87, 35.0,  45.0,  40.0,  90, 88, 2790, 7.5,  30, 'First Team', 'Key Player'),
 ('p_mosquera','Cristian Mosquera',  'Arsenal', 'CB, RB',       21, 'Spain',       80, 25.0,  35.0,  30.0,  84, 82, 640,  3.5,  48, 'First Team', 'Prospect'),
 ('p_odegaard','Martin Odegaard',    'Arsenal', 'AM, CM',       26, 'Norway',      88, 80.0,  95.0,  88.0,  93, 91, 2440, 11.0, 36, 'First Team', 'Captain'),
 ('p_gabriel', 'Gabriel Magalhaes',  'Arsenal', 'CB',           27, 'Brazil',      88, 65.0,  80.0,  72.0,  93, 90, 2680, 9.0,  30, 'First Team', 'Key Player'),
 ('p_timber',  'Jurrien Timber',     'Arsenal', 'RB, CB, LB',   23, 'Netherlands', 83, 40.0,  50.0,  45.0,  87, 84, 1980, 7.0,  36, 'First Team', 'Rotation');

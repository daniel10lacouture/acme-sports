MERGE INTO acme_sports.demo.contracts t
USING (
  SELECT
    'p_' || regexp_extract(fp, 'contract_([a-z]+)\\.pdf', 1) AS player_id,
    try_to_date(ext.contract_start_date, 'd MMMM yyyy') AS c_start,
    try_to_date(ext.contract_end_date,   'd MMMM yyyy') AS c_end,
    CAST(regexp_replace(ext.release_clause_in_euros, '[^0-9]', '') AS DOUBLE) / 1e6 AS clause_m
  FROM (
    SELECT
      _metadata.file_path AS fp,
      ai_extract(
        CAST(ai_parse_document(content) AS STRING),
        array('contract_start_date','contract_end_date','release_clause_in_euros')
      ) AS ext
    FROM READ_FILES('/Volumes/acme_sports/demo/documents/contracts/', format => 'binaryFile')
  )
) src
ON t.player_id = src.player_id
WHEN MATCHED THEN UPDATE SET
  contract_start = src.c_start,
  contract_end   = src.c_end,
  release_clause = src.clause_m,
  last_updated   = current_date();

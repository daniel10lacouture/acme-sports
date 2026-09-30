-- ============================================================================
-- FILE column type showcase (Beta) — acme_sports.demo.contract_files
-- ADDITIVE: does not touch the working demo spine. Reproducible build.
--
-- Verified supported/enabled on FEVM YOUR_WORKSPACE:
--   FILE EXTERNAL DDL, list_files(), to_file(), ai_parse_document(FILE), ai_query — all OK.
-- Docs: https://docs.databricks.com/aws/en/unstructured/file  (admin Previews page gate)
--
-- What it demonstrates: a governed table where each ROW IS A FILE. The `doc`
-- column is a FILE EXTERNAL reference to a contract PDF already in the UC Volume;
-- FILE metadata (uri/size/content_type/checksum) becomes queryable columns; and
-- ai_parse_document + ai_query run DIRECTLY over the FILE column — no separate
-- volume plumbing. Run against Genie-Warehouse (serverless).
-- ============================================================================

-- Step 1 — FILE EXTERNAL table + structured metadata, joined to the players table.
-- Only clean player contracts (contract_<name>.pdf); excludes app/check_run test uploads.
CREATE OR REPLACE TABLE acme_sports.demo.contract_files AS
WITH files AS (
  SELECT lf.path, lf.file, lf.modification_time,
         regexp_extract(lf.path, 'contract_([a-z]+)\\.pdf$', 1) AS player_key
  FROM list_files('/Volumes/acme_sports/demo/documents/contracts/') lf
  WHERE lf.path RLIKE 'contract_[a-z]+\\.pdf$'
)
SELECT
  f.player_key,
  p.player_id, p.name AS player_name, p.positions,
  'contract'            AS doc_type,
  f.file                AS doc,               -- FILE EXTERNAL: governed reference to the PDF
  f.file.uri            AS file_uri,          -- FILE metadata surfaced as columns
  CAST(f.file.size AS BIGINT) AS file_size_bytes,
  f.file.content_type   AS content_type,
  f.file.checksum       AS checksum,
  f.modification_time   AS modified_at
FROM files f
LEFT JOIN acme_sports.demo.players p
  ON lower(p.name) LIKE '%' || f.player_key || '%';

-- Step 2 — AI over the FILE column: ai_parse_document extracts text; ai_query
-- turns each contract into a one-line structured statement (end date + clause).
CREATE OR REPLACE TABLE acme_sports.demo.contract_files AS
WITH parsed AS (
  SELECT
    player_key, player_id, player_name, positions, doc_type, doc,
    file_uri, file_size_bytes, content_type, checksum, modified_at,
    array_join(
      transform(CAST(ai_parse_document(doc):document:elements AS ARRAY<VARIANT>),
                x -> CAST(x:content AS STRING)), ' '
    ) AS doc_text
  FROM acme_sports.demo.contract_files
)
SELECT
  parsed.*,
  ai_query(
    'databricks-gpt-5-mini',
    CONCAT('You are a football club contract analyst. In ONE sentence, state this player''s ',
           'contract end date and release clause if present. Contract text: ', doc_text)
  ) AS ai_summary
FROM parsed;

-- Sanity: 11 rows, all matched, ai_summary populated.
SELECT player_name, positions, file_size_bytes, substr(ai_summary, 1, 120) AS ai_summary
FROM acme_sports.demo.contract_files ORDER BY player_name;

> **Execution evidence — captured live from the Databricks workspace.**
> Run by Daniel Lacouture on 2026-09-30 13:34  against catalog `acme_sports.demo` (Genie-Warehouse, Statement Execution API). Real query output, committed as text.

# 02 — GenAI document intelligence: fields extracted from contract PDFs

`ai_parse_document` + `ai_extract` read the governed contract **PDFs** in the UC Volume and pulled structured fields (release clause, expiry) into the `contracts` Delta table — proof the GenAI stage ran over unstructured documents, not a hand-keyed spreadsheet.

**`contracts` schema:** `player_id`, `contract_start`, `contract_end`, `wage_per_yr`, `release_clause`, `tier`, `transfer_status`, `last_updated`

| player_id | contract_start | contract_end | wage_per_yr | release_clause | tier | transfer_status | last_updated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| p_saka | 2023-07-01 | 2027-06-30 | 12.0 | 180.0 | First Team | Not For Sale | 2026-08-19 |
| p_rice | 2023-07-01 | 2028-06-30 | 14.0 | 200.0 | First Team | Not For Sale | 2026-08-19 |
| p_saliba | 2024-07-01 | 2027-06-30 | 9.5 | 150.0 | First Team | Not For Sale | 2026-08-19 |
| p_raya | 2024-07-01 | 2028-06-30 | 7.5 | 80.0 | First Team | Not For Sale | 2026-08-19 |
| p_odegaard | 2023-07-01 | 2028-06-30 | 11.0 | 160.0 | First Team | Not For Sale | 2026-08-19 |
| p_gabriel | 2022-07-01 | 2027-06-30 | 9.0 | 120.0 | First Team | Not For Sale | 2026-08-19 |
| p_roque | 2025-01-01 | 2029-12-31 | 4.5 | 60.0 | Target | Monitoring | 2026-08-19 |
| p_alvarez | 2024-08-01 | 2028-06-30 | 12.0 | 120.0 | Target | Monitoring | 2026-08-19 |
| p_olise | 2024-07-01 | 2029-06-30 | 10.0 | 90.0 | Target | Monitoring | 2026-08-19 |
| p_tonali | 2023-07-01 | 2028-06-30 | 9.0 | 70.0 | Target | Monitoring | 2026-08-19 |
| p_white |  |  | 8.0 |  | First Team | Available | 2025-08-12 |
| p_norgaard |  |  | 4.0 |  | First Team | Available | 2025-08-12 |

## `acme_sports.demo.contract_files` — governed PDFs as rows (FILE column)

| player_key | player_id | player_name | positions | doc_type | doc | file_uri | file_size_bytes | content_type | checksum | modified_at | doc_text | ai_summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| barcola | p_barcola | Bradley Barcola | LW, RW | contract | {"size":"1252","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_barcola.pdf | 1252 | application/pdf |  | 2026-08-19T01:43:40.000Z | Paris SG - Player Contract PROFESSIONAL PLAYING CONTRACT 1. PARTIES Player Name: Bradle... | Bradley Barcola’s contract ends on 30 June 2028, and it includes a fixed release clause... |
| alvarez | p_alvarez | Julian Alvarez | ST, AM | contract | {"size":"2487","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_alvarez.pdf | 2487 | application/pdf |  | 2026-08-19T01:23:45.000Z | Atletico Madrid - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playi... | Julian Álvarez’s contract ends on 30 June 2028, and it includes a fixed release clause ... |
| roque | p_roque | Vitor Roque | ST | contract | {"size":"2465","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_roque.pdf | 2465 | application/pdf |  | 2026-08-19T01:23:45.000Z | Palmeiras - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playing Con... | Vitor Roque’s contract ends on 31 December 2029, and it includes a fixed release clause... |
| odegaard | p_odegaard | Martin Odegaard | AM, CM | contract | {"size":"2505","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_odegaard.pdf | 2505 | application/pdf |  | 2026-08-19T01:23:44.000Z | Acme Sports FC - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playin... | Martin Odegaard’s contract ends on 30 June 2028, and it includes a fixed release clause... |
| saliba | p_saliba | William Saliba | CB | contract | {"size":"2494","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_saliba.pdf | 2494 | application/pdf |  | 2026-08-19T01:23:45.000Z | Acme Sports FC - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playin... | The contract ends on 30 June 2027 and includes a fixed release clause of EUR 150,000,000. |
| olise | p_olise | Michael Olise | RW, AM | contract | {"size":"2476","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_olise.pdf | 2476 | application/pdf |  | 2026-08-19T01:23:44.000Z | Bayern Munich - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playing... | Michael Olise's contract ends on 30 June 2029, and it includes a fixed EUR 90,000,000 r... |
| rice | p_rice | Declan Rice | DM, CM | contract | {"size":"2498","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_rice.pdf | 2498 | application/pdf |  | 2026-08-19T01:23:44.000Z | Acme Sports FC - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playin... | Declan Rice's contract ends on 30 June 2028, and it includes a fixed release clause of ... |
| gabriel | p_gabriel | Gabriel Magalhaes | CB | contract | {"size":"2496","content_type":"application/pdf","uri":"dbfs:/Volumes/acme_sports/demo/d... | dbfs:/Volumes/acme_sports/demo/documents/contracts/contract_gabriel.pdf | 2496 | application/pdf |  | 2026-08-19T01:23:44.000Z | Acme Sports FC - Player Contract PROFESSIONAL PLAYING CONTRACT This Professional Playin... | Gabriel Magalhaes’s contract ends on 30 June 2027 and includes a fixed release clause o... |


"""AI Contract Analyzer — live parse + compliance flagging at upload.

Closes the loop the demo narrates: a contract PDF lands in the documents volume, then
`ai_parse_document` reads the FILE (via `to_file`) and a single `ai_query` extracts the key
terms AND flags the clauses / compliance / cap-space items a sporting director or CFO could
overlook — live, on the same governed platform, right where the file was uploaded.
"""
import json
from server import dbx

CAT, SCH = dbx.CATALOG, dbx.SCHEMA
ENDPOINT = "databricks-gpt-5-mini"
CONTRACTS_DIR = f"/Volumes/{CAT}/{SCH}/documents/contracts"

_PROMPT = (
    "You are a football club contract analyst supporting a sporting director and CFO. "
    "From the contract text, return STRICT JSON only, with keys: "
    "player (string or null), club (string or null), end_date (string or null), "
    "annual_wage (string or null, include currency), release_clause (string or null, include currency), "
    "flags (array of objects with keys: type, detail, severity where severity is one of high|medium|low), "
    "summary (one sentence). "
    "For flags, surface the clauses and compliance / cap-space items a club could overlook: "
    "release/buy-out clauses, buy-back or matching rights, sell-on percentages, wage escalators, "
    "bonuses and appearance/goal triggers, agent fees, image rights, loyalty/signing bonuses, "
    "and free-transfer risk if the deal is expiring. Keep each detail to one sentence. "
    "No text outside the JSON. Contract text: "
)


def _esc(s):
    return str(s).replace("'", "")


def analyze(filename):
    """Live: ai_parse_document(FILE) -> ai_query -> structured terms + compliance flags."""
    fn = filename.replace("'", "").split("/")[-1]
    path = f"{CONTRACTS_DIR}/{fn}"
    sql = f"""
      WITH parsed AS (
        SELECT array_join(transform(
          CAST(ai_parse_document(to_file('{path}')):document:elements AS ARRAY<VARIANT>),
          x -> CAST(x:content AS STRING)), ' ') AS doc_text
      )
      SELECT ai_query('{ENDPOINT}', CONCAT('{_esc(_PROMPT)}', doc_text)) AS r
      FROM parsed
    """
    rows = dbx.query(sql)
    if not rows:
        return {"ok": False, "filename": fn, "error": "no text parsed from the document"}
    raw = rows[0].get("r") or ""
    data = _parse_json(raw)
    # Record into the live-queried uploaded_docs Delta table so the Genie agent can answer
    # about this contract the moment it's uploaded (volume file-index is not real-time).
    if data:
        try:
            summ = data.get("summary") or (
                f"{data.get('player')} — ends {data.get('end_date')}, "
                f"release clause {data.get('release_clause')}, wage {data.get('annual_wage')}")
            dbx.record_uploaded_doc("contract", data.get("player"), data.get("club"), fn, summ,
                {k: data.get(k) for k in ("end_date", "annual_wage", "release_clause", "flags")})
        except Exception as e:
            print(f"[contract.analyze] uploaded_docs insert skipped: {e}")
    return {"ok": bool(data), "filename": fn, "analysis": data,
            "raw": None if data else raw,
            "source": f"ai_parse_document + ai_query · {ENDPOINT}"}


def _parse_json(raw):
    if not raw:
        return None
    t = raw.strip()
    a, b = t.find("{"), t.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(t[a:b + 1])
        except Exception:
            return None
    return None

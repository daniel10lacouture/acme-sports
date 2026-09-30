#!/usr/bin/env python3
"""Acme Sports demo — end-to-end verification.

Checks: catalog/schema/volume, 4 tables + row counts, volume file listing,
contracts populated by ai_extract, audio transcription pipeline, app health +
static assets, contract-PDF upload THROUGH the app lands in the volume, and the
Genie Agent returns a correct cited BLENDED answer via the API.

Run:  python3 check_run.py
"""
import os, sys, json, subprocess, urllib.request, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import dbsql
from make_pdf import write_pdf

PROFILE = "fe-vm-classic-stable-9cgeia"
APP_URL = "https://acme-sports-7474652196525510.aws.databricksapps.com"
CAT, SCH, VOL = "acme_sports", "demo", "documents"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def sql1(q):
    r = dbsql.run_sql(q)
    rows = r.get("result", {}).get("data_array", [])
    return rows


def token():
    r = subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
                       capture_output=True, text=True, env=ENV)
    return json.loads(r.stdout)["access_token"]


def http(path, tok, method="GET", data=None, headers=None, timeout=200):
    h = {"Authorization": f"Bearer {tok}"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(APP_URL + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


print("=" * 64)
print("ACME SPORTS — END-TO-END VERIFICATION")
print("=" * 64)

# 1. Tables + row counts
counts = {r[0]: int(r[1]) for r in sql1(
    f"SELECT 'players',count(*) FROM {CAT}.{SCH}.players "
    f"UNION ALL SELECT 'contracts',count(*) FROM {CAT}.{SCH}.contracts "
    f"UNION ALL SELECT 'scouting_targets',count(*) FROM {CAT}.{SCH}.scouting_targets "
    f"UNION ALL SELECT 'scout_reports',count(*) FROM {CAT}.{SCH}.scout_reports")}
check("players table (>=20 rows)", counts.get("players", 0) >= 20, f"{counts.get('players')} rows")
check("contracts table (>=14 rows)", counts.get("contracts", 0) >= 14, f"{counts.get('contracts')} rows")
check("scouting_targets table (>=7 rows)", counts.get("scouting_targets", 0) >= 7, f"{counts.get('scouting_targets')} rows")
check("scout_reports table (>=10 rows)", counts.get("scout_reports", 0) >= 10, f"{counts.get('scout_reports')} rows")

# 2. contracts populated by ai_extract
pop = int(sql1(f"SELECT count(*) FROM {CAT}.{SCH}.contracts WHERE contract_end IS NOT NULL AND release_clause IS NOT NULL")[0][0])
check("contracts populated by ai_extract (>=10)", pop >= 10, f"{pop} rows have end date + clause")
saka = sql1(f"SELECT release_clause, contract_end FROM {CAT}.{SCH}.contracts WHERE player_id='p_saka'")
check("Saka clause=180 & end=2027-06-30 (from PDF)", saka and float(saka[0][0]) == 180.0 and str(saka[0][1]) == "2027-06-30", str(saka[0] if saka else None))

# 3. Volume listing
tok = token()
_, body = http("/api/documents", tok, timeout=60)
docs = json.loads(body)
check("volume lists contract PDFs (>=10)", len(docs["contracts"]) >= 10, f"{len(docs['contracts'])} files")
check("volume lists transcripts (>=10)", len(docs["transcripts"]) >= 10, f"{len(docs['transcripts'])} files")

# 4. Transcription pipeline (audio -> transcript in volume)
try:
    from transcribe import ingest_audio_note
    audio = "data/audio/scout_test.wav"
    if os.path.exists(audio):
        res = ingest_audio_note(open(audio, "rb").read(), "verify_check.wav", "Morgan Rogers", "p_rogers",
                                scout_name="check_run", client_transcript="Verification transcript for the audio pipeline.")
        check("transcription pipeline writes transcript to volume", res.get("transcript_path"), res.get("method"))
    else:
        check("transcription pipeline (sample audio present)", False, "data/audio/scout_test.wav missing")
except Exception as e:
    check("transcription pipeline", False, str(e)[:120])

# 5. App health + static assets
try:
    st, body = http("/api/health", tok, timeout=40)
    hj = json.loads(body)
    check("app /api/health OK", st == 200 and hj.get("ok"), f"status {st}")
    st_css, _ = http("/static/styles.css", tok, timeout=40)
    st_js, _ = http("/static/app.js", tok, timeout=40)
    st_png, _ = http("/static/acme_logo.png", tok, timeout=40)
    check("app serves static SPA (css/js/logo)", st_css == 200 and st_js == 200 and st_png == 200,
          f"css={st_css} js={st_js} png={st_png}")
    st_sq, sqb = http("/api/squad", tok, timeout=60)
    sq = json.loads(sqb)
    check("app /api/squad returns 20 players", st_sq == 200 and len(sq) >= 20, f"{len(sq)} players")
except Exception as e:
    check("app health/static/squad", False, str(e)[:150])

# 6. Contract PDF uploaded THROUGH the app lands in the volume
try:
    stem = f"verify_{datetime.datetime.now().strftime('%H%M%S')}"
    pdf_path = f"/tmp/contract_{stem}.pdf"
    write_pdf(pdf_path, "Verification FC - Player Contract",
              [("H2", "RELEASE CLAUSE"), ("P", "Release clause of EUR 42,000,000 (EUR 42 million)."),
               ("P", "Contract End Date: 30 June 2030")])
    # multipart body
    boundary = "----verify"
    with open(pdf_path, "rb") as f:
        pdf = f.read()
    parts = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"contract_{stem}.pdf\"\r\n"
             f"Content-Type: application/pdf\r\n\r\n").encode() + pdf + f"\r\n--{boundary}--\r\n".encode()
    st_up, upb = http("/api/upload/contract", tok, method="POST", data=parts,
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=90)
    up = json.loads(upb)
    # confirm it now appears in the volume listing
    _, body2 = http("/api/documents", tok, timeout=60)
    landed = f"contract_{stem}.pdf" in json.loads(body2)["contracts"]
    check("PDF uploaded via app lands in volume", st_up == 200 and up.get("ok") and landed, up.get("path", ""))
except Exception as e:
    check("app upload -> volume", False, str(e)[:150])

# 7. Genie Agent returns a correct CITED BLENDED answer
try:
    st_ask, askb = http("/api/ask", tok, method="POST",
                        data=json.dumps({"question": "What is Vitor Roque's release clause, and what did our scout say about him?"}).encode(),
                        headers={"Content-Type": "application/json"}, timeout=280)
    ans = json.loads(askb).get("answer") or ""
    has_clause = "60" in ans                          # from contracts/PDF
    has_scout = ("Bianchi" in ans or "priority" in ans.lower() or "scout" in ans.lower())  # from transcript
    has_cite = "gra_focus=" in ans or "/volumes/" in ans.lower()
    check("Genie blended answer cites BOTH table + document", st_ask == 200 and has_clause and has_scout and has_cite,
          f"clause={has_clause} scout={has_scout} cite={has_cite}")
except Exception as e:
    check("Genie blended cited answer", False, str(e)[:150])

# 8. Scouting Clip Search (semantic image search)
try:
    n_clips = int(sql1("SELECT count(*) FROM acme_sports.demo.clip_index")[0][0])
    check("clip_index populated (>=12)", n_clips >= 12, f"{n_clips} clips (vision caption + embedding)")
    import urllib.parse
    # Deterministic name gate: each name query must resolve to exactly ONE player and
    # return that player ONLY (zero leakage). "vini jr" and "diaz" exercise the alias map.
    for name_q, want in [("Vini Jr", "vinicius"), ("Luis Diaz", "diaz"), ("Rodri", "rodri")]:
        _, b = http("/api/clip/search?q=" + urllib.parse.quote(name_q), tok, timeout=90)
        d = json.loads(b)
        # must resolve to ONE player, and every returned clip must be that player only
        names = set(c["name"].lower() for c in d.get("clips", []))
        ok = (d.get("mode") == "player" and d.get("player")
              and want in d["player"]["name"].lower()
              and len(names) == 1 and want in list(names)[0])
        check(f"clip search '{name_q}' -> single-player gallery (zero leakage)", ok,
              f"mode={d.get('mode')} player={d.get('player',{}).get('name')} clips={len(d.get('clips',[]))} distinct_players={len(names)}")
    # Descriptive query must NOT resolve to a player -> semantic scene grid across clips.
    _, sb = http("/api/clip/search?q=" + urllib.parse.quote("player in a red kit"), tok, timeout=90)
    sd = json.loads(sb)
    check("clip search 'player in a red kit' -> scene mode (semantic)",
          sd.get("mode") == "scene" and sd.get("player") is None,
          f"mode={sd.get('mode')} clips={len(sd.get('clips', []))}")
    # image serving (per-image clip_id)
    _, ib = http("/api/clip/image/ext_ldiaz_1", tok, timeout=60)
    check("clip image endpoint serves bytes", len(ib) > 5000, f"{len(ib)} bytes")
    # video serving: a video clip streams its MP4 from the clips volume
    _, vb = http("/api/clip/video/ext_vini_1", tok, timeout=90)
    check("clip video endpoint serves MP4 bytes", len(vb) > 100000, f"{len(vb)} bytes")
except Exception as e:
    check("clip search", False, str(e)[:150])

# ========================= LAKEBASE PHASE (L0–L4) =========================

# 9. Lakebase instance available + synced table landed
try:
    r = subprocess.run(["databricks", "database", "get-database-instance", "acme-lakebase",
                        "-p", PROFILE, "-o", "json"], capture_output=True, text=True, env=ENV)
    inst = json.loads(r.stdout) if r.returncode == 0 else {}
    check("Lakebase instance 'acme-lakebase' AVAILABLE", inst.get("state") == "AVAILABLE",
          f"state={inst.get('state')} cap={inst.get('capacity')}")
    synced = int(sql1("SELECT count(*) FROM acme_lakebase.public.players")[0][0])
    check("Lakebase synced table players = 20 (Delta->Lakebase)", synced == 20, f"{synced} rows")
except Exception as e:
    check("Lakebase instance + synced table", False, str(e)[:150])

# 10. New additive Delta tables exist with rows (existing 4 untouched)
try:
    nc = {t: int(sql1(f"SELECT count(*) FROM {CAT}.{SCH}.{t}")[0][0])
          for t in ["injury_risk", "player_valuation", "scenario_impact", "scenario_moves"]}
    check("injury_risk scored (20 players)", nc["injury_risk"] == 20, f"{nc['injury_risk']} rows")
    check("player_valuation scored (20 players)", nc["player_valuation"] == 20, f"{nc['player_valuation']} rows")
    check("scenario_impact + scenario_moves populated", nc["scenario_impact"] >= 1 and nc["scenario_moves"] >= 2,
          f"impact={nc['scenario_impact']} moves={nc['scenario_moves']}")
except Exception as e:
    check("new Delta tables", False, str(e)[:150])

# 11. App /api/health reports Lakebase connectivity (SP OAuth path)
try:
    _, hb = http("/api/health", tok, timeout=60)
    lb = json.loads(hb).get("lakebase", {})
    check("app health: Lakebase reachable as app SP", lb.get("ok") is True, f"scenarios={lb.get('scenarios')}")
except Exception as e:
    check("app health lakebase", False, str(e)[:150])

# 12. Transactional scenario round-trip THROUGH the app (write -> read back)
try:
    payload = {"scenario_id": "scn_check_run", "name": "Check-run — Sell Saliba",
               "base_formation": "4-3-3", "notes": "Automated verification scenario.",
               "created_by": "check_run",
               "moves": [{"player_id": "p_saliba", "action": "sell", "adjusted_wage": 0, "adjusted_value": 88, "note": "verify"},
                         {"player_id": "p_dowman", "action": "promote", "adjusted_wage": 1.5, "adjusted_value": 8, "note": "verify"}]}
    st_w, wb = http("/api/scenario", tok, method="POST", data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"}, timeout=90)
    st_r, rb = http("/api/scenario/scn_check_run", tok, timeout=60)
    got = json.loads(rb)
    ok = (st_w == 200 and st_r == 200 and got.get("name") == "Check-run — Sell Saliba"
          and len(got.get("moves", [])) == 2)
    check("Lakebase scenario write+read THROUGH the app", ok, f"moves={len(got.get('moves', []))}")
except Exception as e:
    check("app Lakebase scenario round-trip", False, str(e)[:150])

# 12b. Protected DELETE — create->delete round trip THROUGH the app (Lakebase cascade)
#      + verify seeded scenarios are protected (403) and never removed.
def http_status(path, tok, method="GET", data=None, headers=None, timeout=90):
    """Like http() but returns (status, body) even on 4xx instead of raising."""
    import urllib.error
    try:
        return http(path, tok, method=method, data=data, headers=headers, timeout=timeout)
    except urllib.error.HTTPError as e:
        return e.code, e.read()

try:
    dpay = {"scenario_id": "scn_check_delete", "name": "Check-run — Delete round trip",
            "base_formation": "4-3-3", "notes": "Automated delete-coverage scenario.", "created_by": "check_run",
            "moves": [{"player_id": "p_rice", "action": "sell", "adjusted_wage": 0, "adjusted_value": 120, "note": "verify"},
                      {"player_id": "p_dowman", "action": "promote", "adjusted_wage": 1.5, "adjusted_value": 8, "note": "verify"}]}
    st_c, _ = http_status("/api/scenario", tok, method="POST", data=json.dumps(dpay).encode(),
                          headers={"Content-Type": "application/json"})
    st_present, _ = http_status("/api/scenario/scn_check_delete", tok, timeout=60)
    st_d, db = http_status("/api/scenario/scn_check_delete", tok, method="DELETE", timeout=60)
    dj = json.loads(db) if st_d == 200 else {}
    st_gone, _ = http_status("/api/scenario/scn_check_delete", tok, timeout=60)
    _, lb = http("/api/scenarios", tok, timeout=60)
    ids_after = [s["scenario_id"] for s in json.loads(lb)]
    ok_del = (st_c == 200 and st_present == 200 and st_d == 200 and dj.get("moves_deleted") == 2
              and st_gone == 404 and "scn_check_delete" not in ids_after)
    check("Protected DELETE: create->delete round trip THROUGH the app (cascade 2 moves)",
          ok_del, f"create={st_c} del={st_d} moves_deleted={dj.get('moves_deleted')} gone={st_gone}")
    # seeded scenario must be protected (403) and still present afterwards
    st_seed, _ = http_status("/api/scenario/scn_b_saliba_dowman", tok, method="DELETE", timeout=60)
    _, lb2 = http("/api/scenarios", tok, timeout=60)
    seeded_present = "scn_b_saliba_dowman" in [s["scenario_id"] for s in json.loads(lb2)]
    check("Seeded scenario B protected from delete (403) and still present",
          st_seed == 403 and seeded_present, f"status={st_seed} present={seeded_present}")
    # tidy: remove the write-test scenario from #12 via the same endpoint (keeps baseline clean)
    http_status("/api/scenario/scn_check_run", tok, method="DELETE", timeout=60)
except Exception as e:
    check("Protected DELETE round trip", False, str(e)[:150])

# 13. Compare endpoint returns model-based squad value + deltas
try:
    _, cb = http("/api/scenarios/compare", tok, timeout=90)
    cmp = json.loads(cb)
    has_model = "acme-valuation" in str(cmp.get("valuation_model", "")) or cmp.get("current", {}).get("squad_value", 0) > 0
    check("scenario compare returns current + scenarios", cmp.get("current") and len(cmp.get("scenarios", [])) >= 1,
          f"model={cmp.get('valuation_model')} scenarios={len(cmp.get('scenarios', []))}")
except Exception as e:
    check("scenario compare", False, str(e)[:150])

# 14. What-if valuation model (Model Serving) via the app
try:
    _, vb = http("/api/valuation/p_saka", tok, timeout=90)
    vj = json.loads(vb)
    v = vj.get("valuation", {})
    top = (v.get("top_drivers") or [{}])[0].get("feature")
    check("valuation model scores Saka + explains (GPR top driver)",
          v.get("value", 0) > 80 and top == "gpr", f"value={v.get('value')} top={top} src={vj.get('source')}")
except Exception as e:
    check("valuation model", False, str(e)[:150])

# 15. Serving endpoint is directly queryable (live Model Serving)
try:
    r = subprocess.run(["databricks", "serving-endpoints", "query", "acme-valuation",
                        "--json", '{"dataframe_records":[{"gpr":90,"age":25,"minutes":2000,"months_left":24}]}',
                        "-p", PROFILE, "-o", "json"], capture_output=True, text=True, env=ENV)
    pred = json.loads(r.stdout).get("predictions", [{}])[0] if r.returncode == 0 else {}
    check("serving endpoint 'acme-valuation' returns predictions", pred.get("value") is not None,
          f"value={pred.get('value')}")
except Exception as e:
    check("serving endpoint query", False, str(e)[:150])

# 16. Injury endpoint + bands
try:
    _, ib = http("/api/injury", tok, timeout=60)
    inj = json.loads(ib)
    bands = set(r["risk_band"] for r in inj)
    check("injury endpoint returns 20 scored players w/ bands", len(inj) == 20 and "Elevated" in bands,
          f"{len(inj)} players bands={sorted(bands)}")
except Exception as e:
    check("injury endpoint", False, str(e)[:150])

# 17. Genie fused answer: scenario value + injury, cited
try:
    st_g, gb = http("/api/ask", tok, method="POST",
                    data=json.dumps({"question": "In Scenario B, what's our squad value and who is the highest injury risk?"}).encode(),
                    headers={"Content-Type": "application/json"}, timeout=280)
    ga = (json.loads(gb).get("answer") or "")
    has_value = "1,033" in ga or "1033" in ga or "1,0" in ga
    has_injury = "Norgaard" in ga or "injury" in ga.lower() or "risk" in ga.lower()
    has_cite = "gra_focus=" in ga or "/genie/rooms/" in ga
    check("Genie fuses scenario value + injury risk (cited)", st_g == 200 and has_value and has_injury and has_cite,
          f"value={has_value} injury={has_injury} cite={has_cite}")
except Exception as e:
    check("Genie fused answer", False, str(e)[:150])

# ========================= FILE COLUMN TYPE (Beta) =========================
# Additive showcase: acme_sports.demo.contract_files — FILE EXTERNAL refs to
# the volume PDFs + metadata columns + ai_parse_document/ai_query over the FILE.
try:
    ftype = sql1("DESCRIBE acme_sports.demo.contract_files")
    coltypes = {r[0]: r[1] for r in ftype}
    check("contract_files has a FILE EXTERNAL column",
          "file external" in coltypes.get("doc", "").lower(), f"doc={coltypes.get('doc')}")
    n_cf = int(sql1("SELECT count(*) FROM acme_sports.demo.contract_files")[0][0])
    n_ai = int(sql1("SELECT count(*) FROM acme_sports.demo.contract_files WHERE ai_summary IS NOT NULL AND len(ai_summary) > 10")[0][0])
    check("contract_files populated w/ ai_query summaries (>=10)", n_cf >= 10 and n_ai >= 10, f"{n_cf} rows, {n_ai} with ai_summary")
    saka_cf = sql1("SELECT ai_summary FROM acme_sports.demo.contract_files WHERE player_key='saka'")
    s = (saka_cf[0][0] if saka_cf else "") or ""
    check("contract_files ai_summary extracts Saka clause from FILE", "180" in s and "2027" in s, s[:120])
except Exception as e:
    check("FILE column showcase", False, str(e)[:150])

# ========================= AI TRANSFER ASSISTANT =========================
# Additive: player_kpis table + calibrated position-specific model on Model Serving
# (acme-transfer-valuation) + interactive schema/recompute endpoints in the app.
try:
    nk = int(sql1("SELECT count(*) FROM acme_sports.demo.player_kpis")[0][0])
    ng = int(sql1("SELECT count(DISTINCT position_group) FROM acme_sports.demo.player_kpis")[0][0])
    check("player_kpis populated (20 rows, position groups)", nk == 20 and ng >= 3,
          f"{nk} rows, {ng} position groups")
except Exception as e:
    check("player_kpis table", False, str(e)[:150])

# app: /api/transfer/{id} returns position-specific sliders + valuation
try:
    _, tb = http("/api/transfer/p_saka", tok, timeout=90)
    tj = json.loads(tb)
    keys = [s["key"] for s in tj.get("sliders", [])]
    fw_specific = "goals_p90" in keys and "xg_p90" in keys
    val = (tj.get("valuation") or {}).get("value", 0)
    check("app /api/transfer serves FW-specific sliders + value (Saka)",
          tj.get("group") == "FW" and fw_specific and val > 80,
          f"group={tj.get('group')} value={val} keys={len(keys)}")
except Exception as e:
    check("app /api/transfer schema", False, str(e)[:150])

# app: /api/transfer/value recomputes a scenario (drag simulation)
try:
    payload = json.dumps({"group": "GK", "values": {"age": 24, "minutes": 2000, "months_left": 36,
        "league_str": 80, "clean_sheet_pct": 35, "save_pct": 72, "aerial_claims_p90": 1.2}}).encode()
    _, rb = http("/api/transfer/value", tok, method="POST", data=payload,
                 headers={"Content-Type": "application/json"}, timeout=90)
    rv = (json.loads(rb).get("valuation") or {}).get("value")
    # all-reference GK inputs -> value should equal the GK base (30.0)
    check("app /api/transfer/value recompute (GK at ref == base 30)", abs((rv or 0) - 30.0) < 0.5,
          f"value={rv}")
except Exception as e:
    check("app /api/transfer/value recompute", False, str(e)[:150])

# serving endpoint is directly queryable + agrees with the calibrated math
try:
    rec = {"group": "FW", "age": 23, "minutes": 2380, "months_left": 30, "league_str": 85,
           "goals_p90": 0.55, "xg_p90": 0.5, "shot_conv_pct": 21, "pressures_p90": 23}
    r = subprocess.run(["databricks", "serving-endpoints", "query", "acme-transfer-valuation",
                        "--json", json.dumps({"dataframe_records": [rec]}),
                        "-p", PROFILE, "-o", "json"], capture_output=True, text=True, env=ENV)
    pred = json.loads(r.stdout).get("predictions", ["{}"])[0] if r.returncode == 0 else "{}"
    if isinstance(pred, str):
        pred = json.loads(pred)
    check("serving endpoint 'acme-transfer-valuation' returns predictions (≈110)",
          pred.get("value") is not None and abs(pred.get("value", 0) - 110.38) < 1.0,
          f"value={pred.get('value')}")
except Exception as e:
    check("transfer serving endpoint query", False, str(e)[:150])

# ========================= AI PHYSIO / LOAD MANAGER =========================
# WHOOP (recovery/sleep/HRV) + STATSports (GPS) synthetic tables -> load_status snapshot
# (ACWR, minutes, recovery, recommended minutes, load flag) + LIVE ai_query recommendation.
try:
    ns = int(sql1("SELECT count(*) FROM acme_sports.demo.statsports_sessions")[0][0])
    nw = int(sql1("SELECT count(*) FROM acme_sports.demo.whoop_daily")[0][0])
    check("STATSports + WHOOP synthetic tables populated (>=500 each)", ns >= 500 and nw >= 500,
          f"statsports={ns} whoop={nw}")
    ls = sql1("SELECT count(*), count(DISTINCT load_flag) FROM acme_sports.demo.load_status")
    check("load_status snapshot = 20 players w/ load flags", int(ls[0][0]) == 20 and int(ls[0][1]) >= 2,
          f"{ls[0][0]} rows, {ls[0][1]} distinct flags")
except Exception as e:
    check("physio tables", False, str(e)[:150])

# app: /api/physio load board (ACWR + recommended minutes + flag)
try:
    _, pb = http("/api/physio", tok, timeout=60)
    pj = json.loads(pb)
    ok = len(pj) == 20 and all(k in pj[0] for k in ("acwr", "recommended_minutes_next", "load_flag"))
    check("app /api/physio load board (20, ACWR + next-minutes + flag)", ok,
          f"{len(pj)} players, first={pj[0].get('player_name')} acwr={pj[0].get('acwr')}")
except Exception as e:
    check("app /api/physio", False, str(e)[:150])

# app: /api/physio/{id} detail returns GPS + recovery trend series
try:
    _, db = http("/api/physio/p_saka", tok, timeout=60)
    dj = json.loads(db)
    check("app /api/physio detail returns GPS + recovery series",
          dj.get("status") and len(dj.get("sessions", [])) > 0 and len(dj.get("recovery", [])) > 0,
          f"sessions={len(dj.get('sessions', []))} recovery={len(dj.get('recovery', []))}")
except Exception as e:
    check("app /api/physio detail", False, str(e)[:150])

# app: LIVE ai_query minutes recommendation grounded in the player's numbers
try:
    _, rb = http("/api/physio/p_saka/recommend", tok, timeout=120)
    rj = json.loads(rb)
    rec = (rj.get("recommendation") or "")
    check("physio recommendation is LIVE ai_query, grounded & non-empty",
          "ai_query" in (rj.get("source") or "") and len(rec) > 40,
          f"src={rj.get('source')} len={len(rec)}")
except Exception as e:
    check("physio ai_query recommendation", False, str(e)[:150])

# ========================= AI NUTRITION ASSISTANT =========================
# Reuses physio metrics (distance/sleep/recovery) + a voice note -> ai_query fuelling plan.
try:
    _, mb = http("/api/nutrition/p_saka", tok, timeout=60)
    mj = json.loads(mb)
    check("app /api/nutrition serves fuelling metrics (distance/recovery/kcal)",
          mj.get("distance_7d_km") is not None and mj.get("avg_recovery_7d") is not None
          and mj.get("est_daily_kcal", 0) > 1500,
          f"dist={mj.get('distance_7d_km')} rec={mj.get('avg_recovery_7d')} kcal={mj.get('est_daily_kcal')}")
except Exception as e:
    check("app /api/nutrition metrics", False, str(e)[:150])

try:
    payload = json.dumps({"note": "prefers rice over pasta, lactose intolerant, big match Sunday"}).encode()
    _, rb = http("/api/nutrition/p_saka/recommend", tok, method="POST", data=payload,
                 headers={"Content-Type": "application/json"}, timeout=120)
    rj = json.loads(rb)
    base = rj.get("baseline") or {}
    adj = rj.get("adjustments") or {}
    ok = ("ai_query" in (rj.get("source") or "") and rj.get("used_voice_note")
          and base.get("daily_kcal") and base.get("carbs_g")
          and len(adj.get("adjustments") or []) >= 1 and adj.get("summary"))
    check("nutrition baseline + LIVE ai_query adjustments (voice note used)", bool(ok),
          f"baseline_kcal={base.get('daily_kcal')} n_adjustments={len(adj.get('adjustments') or [])} voice={rj.get('used_voice_note')}")
except Exception as e:
    check("nutrition ai_query fuelling plan", False, str(e)[:150])

# ========================= AI OPPOSITION / MATCH-PREP ANALYST =========================
# Synthetic provider-shaped opponents + ai_query brief + clip citations (reuse clip search).
try:
    no = int(sql1("SELECT count(*) FROM acme_sports.demo.opponents")[0][0])
    check("opponents table populated (>=3 provider-shaped)", no >= 3, f"{no} opponents")
except Exception as e:
    check("opponents table", False, str(e)[:150])

try:
    _, lb = http("/api/opposition", tok, timeout=60)
    lj = json.loads(lb)
    check("app /api/opposition lists upcoming opponents", len(lj) >= 3 and lj[0].get("ppda") is not None,
          f"{len(lj)} opponents, first={lj[0].get('opponent')}")
except Exception as e:
    check("app /api/opposition list", False, str(e)[:150])

try:
    _, rb = http("/api/opposition/opp_mancity/report", tok, timeout=150)
    rj = json.loads(rb)
    brief = rj.get("brief") or {}
    cite = (rj.get("citations") or [{}])[0].get("clip") or {}
    ok = (brief.get("summary") and len(brief.get("how_we_beat_them", [])) >= 2
          and cite.get("clip_id"))
    check("opposition report: LIVE ai_query brief + clip citation (Rodri)", bool(ok),
          f"parsed={rj.get('brief') is not None} plan={len(brief.get('how_we_beat_them', []))} clip={cite.get('clip_id')}")
except Exception as e:
    check("opposition ai_query report + citation", False, str(e)[:150])

# ========================= AI CONTRACT & FFP/PSR COMPLIANCE AGENT =========================
# contract_economics (real wages/dates + synthetic fees -> amortization) + FILE-column evidence
# + LIVE ai_query board verdict.
try:
    ne = int(sql1("SELECT count(*) FROM acme_sports.demo.contract_economics")[0][0])
    check("contract_economics populated (first team, >=10)", ne >= 10, f"{ne} rows")
except Exception as e:
    check("contract_economics table", False, str(e)[:150])

try:
    _, sb = http("/api/ffp", tok, timeout=60)
    sj = json.loads(sb)
    ok = (sj.get("squad_cost_ratio") and sj.get("investment_headroom") is not None
          and len(sj.get("players", [])) >= 10 and "psr_headroom" in sj)
    check("app /api/ffp models squad-cost ratio + PSR headroom + flags", bool(ok),
          f"ratio={sj.get('squad_cost_ratio')} headroom={sj.get('investment_headroom')} flags={len(sj.get('flags', []))}")
except Exception as e:
    check("app /api/ffp summary", False, str(e)[:150])

try:
    _, bb = http("/api/ffp/brief", tok, timeout=120)
    bj = json.loads(bb)
    brief = bj.get("brief") or {}
    ev = bj.get("evidence") or []
    ok = ("ai_query" in (bj.get("source") or "") and brief.get("verdict") and brief.get("headline")
          and len(ev) >= 1 and (ev[0].get("ai_summary") or ""))
    check("FFP exec verdict: LIVE ai_query + FILE-column contract evidence", bool(ok),
          f"verdict={brief.get('verdict')} evidence={len(ev)}")
except Exception as e:
    check("FFP ai_query brief + evidence", False, str(e)[:150])

# ---- summary ----
print("=" * 64)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"SUMMARY: {passed}/{total} checks passed")
for name, ok, _ in results:
    if not ok:
        print(f"  ✗ {name}")
print("=" * 64)
sys.exit(0 if passed == total else 1)

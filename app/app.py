"""Acme Sports — Databricks App (FastAPI + static vanilla-JS SPA)."""
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from server import dbx, lakebase, impact, valuation, physio, transfer, nutrition, opposition, ffp, contract

app = FastAPI(title="Acme Sports")

CAT, SCH = dbx.CATALOG, dbx.SCHEMA


@app.get("/api/health")
def health():
    out = {"ok": True, "catalog": CAT, "schema": SCH, "agent": dbx.GENIE_AGENT_ID}
    try:
        out["lakebase"] = lakebase.health()
    except Exception as e:
        out["lakebase"] = {"ok": False, "error": str(e)[:200]}
    return out


@app.get("/api/squad")
def squad():
    rows = dbx.query(f"""
      SELECT p.player_id, p.name, p.club, p.positions, p.age, p.nationality, p.gpr,
             p.est_valuation_low, p.est_valuation_high, p.gpv, p.wage_per_yr,
             p.months_left, p.tier, p.status, p.team_style_fit, p.player_style_fit, p.minutes,
             c.contract_end, c.release_clause, c.transfer_status
      FROM {CAT}.{SCH}.players p
      LEFT JOIN {CAT}.{SCH}.contracts c USING(player_id)
      ORDER BY p.gpr DESC""")
    return rows


@app.get("/api/summary")
def summary():
    dist = dbx.query(f"""
      SELECT CASE WHEN gpr>=90 THEN '90+' WHEN gpr>=85 THEN '85-89'
                  WHEN gpr>=80 THEN '80-84' WHEN gpr>=75 THEN '75-79'
                  ELSE '<75' END AS band, count(*) AS n
      FROM {CAT}.{SCH}.players GROUP BY 1""")
    tiers = dbx.query(f"SELECT tier, count(*) n FROM {CAT}.{SCH}.players GROUP BY tier")
    agg = dbx.query(f"""SELECT count(*) squad_size, round(avg(gpr),1) avg_gpr,
             round(sum(wage_per_yr),1) wage_bill, round(sum(gpv),0) squad_value
             FROM {CAT}.{SCH}.players""")
    return {"gpr_bands": dist, "tiers": tiers, "totals": agg[0] if agg else {}}


@app.get("/api/player/{player_id}")
def player(player_id: str):
    rows = dbx.query(f"""
      SELECT p.*, c.contract_start, c.contract_end, c.release_clause, c.transfer_status
      FROM {CAT}.{SCH}.players p LEFT JOIN {CAT}.{SCH}.contracts c USING(player_id)
      WHERE p.player_id = '{player_id.replace("'", "")}'""")
    if not rows:
        raise HTTPException(404, "player not found")
    reports = dbx.query(f"""SELECT scout_name, report_date, status, summary
      FROM {CAT}.{SCH}.scout_reports WHERE player_id='{player_id.replace("'","")}'
      ORDER BY report_date DESC""")
    return {"player": rows[0], "scout_reports": reports}


@app.get("/api/scouting")
def scouting():
    return dbx.query(f"""
      SELECT s.list_name, s.player_id, p.name, s.club, s.positions, s.country,
             s.gpr, s.months_left, c.release_clause
      FROM {CAT}.{SCH}.scouting_targets s
      JOIN {CAT}.{SCH}.players p USING(player_id)
      LEFT JOIN {CAT}.{SCH}.contracts c USING(player_id)
      ORDER BY s.list_name, s.gpr DESC""")


# ---- LAKEBASE: what-if scenarios (transactional OLTP) ----
@app.get("/api/scenarios")
def scenarios_list():
    return lakebase.list_scenarios()


@app.get("/api/scenario/{scenario_id}")
def scenario_get(scenario_id: str):
    s = lakebase.get_scenario(scenario_id)
    if not s:
        raise HTTPException(404, "scenario not found")
    return s


@app.post("/api/scenario")
def scenario_save(payload: dict):
    if not (payload or {}).get("name"):
        raise HTTPException(400, "name required")
    try:
        saved = lakebase.save_scenario(payload)
    except Exception as e:
        raise HTTPException(500, f"lakebase write failed: {e}")
    try:
        impact.sync_to_delta(saved["scenario_id"])  # make it answerable in Acme Scout
    except Exception as e:
        print(f"[scenario_save] delta sync skipped: {e}")
    return saved


@app.delete("/api/scenario/{scenario_id}")
def scenario_delete(scenario_id: str):
    # Seeded/demo scenarios (Scenario B) are protected — never deletable.
    try:
        result = lakebase.delete_scenario(scenario_id)
    except lakebase.SeededScenarioError:
        raise HTTPException(403, "seeded scenario is protected and cannot be deleted")
    except Exception as e:
        raise HTTPException(500, f"lakebase delete failed: {e}")
    if not result.get("found"):
        raise HTTPException(404, "scenario not found")
    try:
        impact.delete_from_delta(scenario_id)  # keep the Genie-facing mirror in sync (best-effort)
    except Exception as e:
        print(f"[scenario_delete] delta mirror cleanup skipped: {e}")
    return result


@app.get("/api/scenarios/compare")
def scenarios_compare():
    return impact.compare()


# ---- L3: injury & load-risk (scored Delta table) ----
@app.get("/api/injury")
def injury():
    try:
        return dbx.query(f"""
          SELECT player_id, name, tier, risk_score, risk_band, availability, top_factor,
                 risk_note, recent_minutes_load, sprints_per90, high_accel_per90,
                 match_density_14d, prior_injuries, contributions_json
          FROM {CAT}.{SCH}.injury_risk ORDER BY risk_score DESC""")
    except Exception:
        return []


# ---- L2: what-if valuation model (Model Serving) ----
@app.get("/api/valuation/{player_id}")
def valuation_explain(player_id: str):
    rows = dbx.query(f"""
      SELECT player_id, name, gpr, age, minutes, months_left, gpv,
             est_valuation_low, est_valuation_high
      FROM {CAT}.{SCH}.players WHERE player_id='{player_id.replace(chr(39),'')}'""")
    if not rows:
        raise HTTPException(404, "player not found")
    p = rows[0]
    return {"player_id": p["player_id"], "name": p["name"], "gpv": p.get("gpv"),
            "valuation": valuation.explain(p), "source": valuation.endpoint_status()}


# ---- AI Transfer Assistant (interactive position-specific valuation, Model Serving) ----
@app.get("/api/transfer/{player_id}")
def transfer_schema(player_id: str):
    s = transfer.schema(player_id)
    if not s:
        raise HTTPException(404, "player not found")
    return s


@app.post("/api/transfer/value")
def transfer_value(payload: dict):
    grp = (payload or {}).get("group")
    values = (payload or {}).get("values") or {}
    if not grp:
        raise HTTPException(400, "group required")
    use_ep = bool((payload or {}).get("use_endpoint", True))
    v = transfer.score(grp, values, use_endpoint=use_ep)
    return {"valuation": v, "source": transfer.endpoint_status()}


# ---- AI Physio / Load Manager (Whoop + STATSports load data) ----
@app.get("/api/physio")
def physio_status():
    try:
        return physio.load_status()
    except Exception:
        return []


@app.get("/api/physio/{player_id}")
def physio_detail(player_id: str):
    d = physio.player_detail(player_id)
    if not d:
        raise HTTPException(404, "player not found")
    return d


@app.get("/api/physio/{player_id}/recommend")
def physio_recommend(player_id: str):
    r = physio.recommend(player_id)
    if not r:
        raise HTTPException(404, "player not found")
    return r


@app.post("/api/physio/{player_id}/recommend")
def physio_recommend_note(player_id: str, payload: dict = None):
    r = physio.recommend(player_id, (payload or {}).get("note"))
    if not r:
        raise HTTPException(404, "player not found")
    return r


# ---- AI Nutrition Assistant (physio metrics + voice note -> ai_query fuelling plan) ----
@app.get("/api/nutrition/{player_id}")
def nutrition_metrics(player_id: str):
    m = nutrition.metrics(player_id)
    if not m:
        raise HTTPException(404, "player not found")
    return m


@app.post("/api/nutrition/{player_id}/recommend")
def nutrition_recommend(player_id: str, payload: dict = None):
    note = (payload or {}).get("note")
    r = nutrition.recommend(player_id, note)
    if not r:
        raise HTTPException(404, "player not found")
    return r


# ---- AI Opposition / Match-Prep Analyst (opponent metrics + clips -> ai_query brief) ----
@app.get("/api/opposition")
def opposition_list():
    return opposition.list_opponents()


@app.get("/api/opposition/{opponent_id}/report")
def opposition_report(opponent_id: str):
    r = opposition.report(opponent_id)
    if not r:
        raise HTTPException(404, "opponent not found")
    return r


# ---- AI Contract & FFP/PSR Compliance Agent (contracts + FILE table -> compliance) ----
@app.get("/api/ffp")
def ffp_summary():
    return ffp.summary()


@app.get("/api/ffp/brief")
def ffp_brief():
    return ffp.exec_brief()


@app.get("/api/ffp/scenarios")
def ffp_scenarios():
    return ffp.scenarios()


@app.post("/api/ask")
def ask(payload: dict):
    q = (payload or {}).get("question", "").strip()
    if not q:
        raise HTTPException(400, "question required")
    return dbx.ask_genie(q)


@app.get("/api/documents")
def documents():
    return {"contracts": dbx.list_volume("contracts"),
            "transcripts": dbx.list_volume("transcripts"),
            "audio": dbx.list_volume("audio")}


# ---- WORKING UPLOAD FLOW A: contract PDF -> documents volume ----
@app.post("/api/upload/contract")
async def upload_contract(file: UploadFile = File(...)):
    data = await file.read()
    name = os.path.basename(file.filename or "contract.pdf").replace(" ", "_")
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    path = dbx.upload_to_volume(f"contracts/{name}", data)
    return {"ok": True, "path": path, "bytes": len(data), "filename": name}


# ---- CONTRACT ANALYZER: live ai_parse_document + ai_query -> terms + compliance flags ----
@app.get("/api/contract/analyze")
def contract_analyze(name: str):
    if not name.strip():
        raise HTTPException(400, "name required")
    try:
        return contract.analyze(name)
    except Exception as e:
        raise HTTPException(500, f"contract analysis failed: {e}")


# ---- WORKING UPLOAD FLOW B: audio scout note -> transcribe -> volume ----
@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...),
                       player_name: str = Form("Unknown Player"),
                       player_id: str = Form("p_unknown"),
                       scout_name: str = Form("App Upload"),
                       transcript: str = Form(None)):
    data = await file.read()
    name = os.path.basename(file.filename or "note.wav")
    try:
        res = dbx.ingest_audio_note(data, name, player_name, player_id, scout_name, transcript)
        return {"ok": True, **res}
    except Exception as e:
        raise HTTPException(500, f"transcription/ingest failed: {e}")


# ---- Scouting Clip Search (semantic image search) ----
@app.get("/api/clip/search")
def clip_search(q: str, k: int = 8):
    if not q.strip():
        raise HTTPException(400, "q required")
    return dbx.search_clips(q, k)


@app.get("/api/clip/image/{clip_id}")
def clip_image(clip_id: str):
    data, ct = dbx.read_clip_image(clip_id)
    if not data:
        raise HTTPException(404, "clip not found")
    return Response(content=data, media_type=ct,
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/clip/frame/{clip_id}/{idx}")
def clip_frame(clip_id: str, idx: int):
    try:
        data = dbx.read_clip_frame(clip_id, idx)
    except Exception:
        data = None
    if not data:
        raise HTTPException(404, "frame not found")
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/clip/video/{clip_id}")
def clip_video(clip_id: str):
    data, ct = dbx.read_clip_video(clip_id)
    if not data:
        raise HTTPException(404, "video clip not found")
    return Response(content=data, media_type=ct,
                    headers={"Cache-Control": "public, max-age=3600",
                             "Accept-Ranges": "bytes"})


# ---- static SPA ----
STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))

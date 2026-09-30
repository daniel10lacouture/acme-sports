"""Databricks access layer for the Acme Sports app.

Dual-mode: in Databricks Apps, WorkspaceClient() auto-authenticates as the app
service principal. Locally, it uses the DATABRICKS_PROFILE (or CLI default).
Covers: SQL (Statement Execution), UC Volume writes (Files API), and the Genie
Agent-mode conversation API (SSE) for blended structured+document answers.
"""
import os, json, urllib.request, base64, datetime, math, re, unicodedata
from databricks.sdk import WorkspaceClient

WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "84c07276d33bc0a0")
CATALOG = os.environ.get("CATALOG", "acme_sports")
SCHEMA = os.environ.get("SCHEMA", "demo")
VOLUME = os.environ.get("VOLUME", "documents")
GENIE_AGENT_ID = os.environ.get("GENIE_AGENT_ID", "01f19b59e604108aba34eda9d7e97569")
TRANSCRIBE_ENDPOINT = os.environ.get("TRANSCRIBE_ENDPOINT", "")
EMBED_ENDPOINT = os.environ.get("EMBED_ENDPOINT", "databricks-gte-large-en")
VOL_BASE = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
CLIPS_VOL = f"/Volumes/{CATALOG}/{SCHEMA}/clips"

_IS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))


def _client() -> WorkspaceClient:
    if _IS_APP:
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE", "fe-vm-classic-stable-9cgeia")
    return WorkspaceClient(profile=profile)


w = _client()


def _host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "") if _IS_APP else w.config.host
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return host or w.config.host


def _token() -> str:
    hdr = w.config.authenticate()
    return hdr["Authorization"].replace("Bearer ", "") if hdr else ""


# ---------- SQL ----------
def query(sql: str):
    """Run SQL on the Genie warehouse; return list[dict]."""
    r = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID, statement=sql, wait_timeout="50s")
    # poll if needed
    import time
    sid = r.statement_id
    while r.status and r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(1)
        r = w.statement_execution.get_statement(sid)
    if not r.result or not r.manifest:
        return []
    cols = [c.name for c in r.manifest.schema.columns]
    rows = r.result.data_array or []
    return [dict(zip(cols, row)) for row in rows]


# ---------- Volume writes (Files API) ----------
def upload_to_volume(rel_path: str, data: bytes) -> str:
    """PUT bytes into the documents volume. rel_path e.g. 'contracts/x.pdf'."""
    vpath = f"{VOL_BASE}/{rel_path}"
    url = f"{_host()}/api/2.0/fs/files{vpath}?overwrite=true"
    req = urllib.request.Request(url, data=data, method="PUT",
        headers={"Authorization": f"Bearer {_token()}",
                 "Content-Type": "application/octet-stream"})
    urllib.request.urlopen(req, timeout=120)
    return vpath


def list_volume(subdir: str):
    """List filenames under a volume subdir via the Files API directory listing."""
    url = f"{_host()}/api/2.0/fs/directories{VOL_BASE}/{subdir}"
    req = urllib.request.Request(url, method="GET",
        headers={"Authorization": f"Bearer {_token()}"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=60))
        return [c.get("name", "") for c in d.get("contents", []) if not c.get("is_directory")]
    except Exception:
        return []


# ---------- Transcription ----------
def transcribe(audio_bytes: bytes, filename: str, client_transcript: str = None):
    if TRANSCRIBE_ENDPOINT:
        try:
            b64 = base64.b64encode(audio_bytes).decode()
            body = json.dumps({"inputs": {"audio": [b64], "filename": [filename]}}).encode()
            url = f"{_host()}/serving-endpoints/{TRANSCRIBE_ENDPOINT}/invocations"
            req = urllib.request.Request(url, data=body, method="POST",
                headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=180))
            preds = d.get("predictions") or d.get("text") or d
            text = preds[0] if isinstance(preds, list) else str(preds)
            return text.strip(), f"whisper:{TRANSCRIBE_ENDPOINT}"
        except Exception as e:
            print(f"[transcribe] endpoint failed: {e}")
    if client_transcript:
        return client_transcript.strip(), "browser-web-speech-api"
    raise RuntimeError("No transcription available")


def _sqlstr(s):
    """Quote a Python value as a Spark SQL string literal (NULL-safe, quote-doubled)."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def _ascii_name(s):
    """ASCII-fold a name so typed queries match (e.g. 'Luis Díaz' -> 'Luis Diaz').
    The accented original is preserved in the summary text for display."""
    if not s:
        return s
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode() or str(s)


def record_uploaded_doc(doc_type, player_name, club, source_file, summary, details=None):
    """Insert a row into the live-queried uploaded_docs Delta table so the Genie agent
    can answer about a doc the instant it's uploaded — no volume file-index lag.
    player_name is ASCII-folded so accent-free typed queries (Genie NL->SQL) match."""
    import uuid as _uuid
    player_name = _ascii_name(player_name)
    did = f"{doc_type}_{_uuid.uuid4().hex[:10]}"
    dj = json.dumps(details) if isinstance(details, (dict, list)) else (details or None)
    sql = (f"INSERT INTO {CATALOG}.{SCHEMA}.uploaded_docs "
           f"(doc_id, doc_type, player_name, club, uploaded_at, source_file, summary, details) VALUES ("
           f"{_sqlstr(did)}, {_sqlstr(doc_type)}, {_sqlstr(player_name)}, {_sqlstr(club)}, "
           f"current_timestamp(), {_sqlstr(source_file)}, {_sqlstr(summary)}, {_sqlstr(dj)})")
    query(sql)
    return did


def ingest_audio_note(audio_bytes, filename, player_name, player_id,
                      scout_name="App Upload", client_transcript=None):
    text, method = transcribe(audio_bytes, filename, client_transcript)
    # UNIQUE name per note so every note persists (the old code derived the stem from a
    # FIXED upload filename — "scout_note.webm" — so each note overwrote the last).
    raw = (player_id or "").strip()
    slug = "general" if raw in ("", "p_unknown") else (
        re.sub(r"[^a-z0-9]+", "-", raw.replace("p_", "", 1).lower()).strip("-") or "general")
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{slug}_{ts}"
    audio_path = upload_to_volume(f"audio/{stem}.wav", audio_bytes)
    doc = (f"ACME SPORTS — SCOUT NOTE (VOICE TRANSCRIPT)\n"
           f"Player: {player_name}\nPlayer ID: {player_id}\nScout: {scout_name}\n"
           f"Date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
           f"Fixture observed: (uploaded via Acme Sports app)\nStatus: Active\n\nSUMMARY:\n{text}\n")
    tx_path = upload_to_volume(f"transcripts/scout_note_{stem}.txt", doc.encode())
    # ALSO record into the live-queried Delta table so the Genie agent can answer about
    # this note immediately (the volume file-index is not real-time).
    try:
        record_uploaded_doc("voice_note", player_name, None, f"scout_note_{stem}.txt",
                             text, {"scout": scout_name, "player_id": player_id})
    except Exception as e:
        print(f"[ingest_audio_note] uploaded_docs insert skipped: {e}")
    return {"transcript": text, "method": method, "transcript_path": tx_path, "audio_path": audio_path}


# ---------- Scouting Clip Search (semantic image search) ----------
def _embed(text):
    body = json.dumps({"input": [text]}).encode()
    url = f"{_host()}/serving-endpoints/{EMBED_ENDPOINT}/invocations"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return d["data"][0]["embedding"]


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _name_resolve(q, names_by_player):
    """If the query reads like a player's name, return that player_id (deterministic
    gate for the single-player gallery). Descriptive/scene queries return None and
    fall through to the embedding ranker. Tokens <3 chars (jr, fc) are ignored.

    Resolution: alias map OR token-prefix matching must resolve to exactly one player.
    Alias matches are checked first (accent-insensitive normalization), then token logic."""

    # Explicit alias map: player_id -> set of normalized aliases
    ALIASES = {
        'ext_vini': {'vini', 'vinicius', 'vinicius jr', 'vini jr', 'vinic'},
        'ext_ldiaz': {'luis diaz', 'diaz', 'luis diaz', 'lucho'},
        'ext_raphinha': {'raphinha', 'rapha', 'raphinha barcelona', 'raphael dias'},
        'ext_haaland': {'haaland', 'erling haaland', 'erling', 'haaland9'}
    }

    nq = _norm(q)
    qtok = [t for t in nq.split() if len(t) >= 3]

    if not qtok:
        return None

    # Check alias map first
    alias_hits = []
    for pid, aliases in ALIASES.items():
        if nq in aliases or any(_norm(alias) == nq for alias in aliases):
            alias_hits.append(pid)

    if len(alias_hits) == 1:
        return alias_hits[0]
    if len(alias_hits) > 1:
        return None  # Ambiguous alias match

    # Token-based matching (existing logic)
    hits = []
    for pid, nm in names_by_player.items():
        ntok = set(_norm(nm).split())
        if all(any(nt == t or nt.startswith(t) or t.startswith(nt) for nt in ntok) for t in qtok):
            hits.append(pid)

    return hits[0] if len(hits) == 1 else None


def _club_resolve(q, clubs):
    """If the query reads like a CLUB name, return the canonical club string (deterministic
    gallery gate). Matches when the normalized query equals a club, or every query token
    (>=3 chars) is covered by that club's tokens — e.g. 'real madrid', 'madrid', 'bayern'.
    Returns the club only if exactly one club matches; otherwise None (falls through)."""
    nq = _norm(q)
    qtok = [t for t in nq.split() if len(t) >= 3]
    if not qtok:
        return None
    hits = []
    for club in clubs:
        ctok = set(_norm(club).split())
        if nq == _norm(club) or all(any(ct == t or ct.startswith(t) for ct in ctok) for t in qtok):
            hits.append(club)
    return hits[0] if len(hits) == 1 else None


def search_clips(q, k=8):
    """Resolve a query to the best-matching PLAYER and return that player's whole
    gallery (player mode). If the query does not resolve to a player name, return a
    ranked grid across all clips (scene mode) — deterministic via name resolution only."""
    qe = _embed(q)
    # Fetch new schema columns; fall back if null (pre-backfill compatibility).
    # VIDEO-ONLY: the scouting index is exclusively player highlight videos now, so we
    # hard-filter to media_type='video' — a search never surfaces a still image.
    rows = query(f"SELECT clip_id, player_id, name, player_name, club, file, caption, "
                 f"embedding_json, media_type, video_url, poster_path "
                 f"FROM {CATALOG}.{SCHEMA}.clip_index WHERE media_type = 'video'")
    scored = []
    for r in rows:
        emb = json.loads(r["embedding_json"])
        # Fall back to name if player_name is null (pre-backfill)
        pname = r.get("player_name") or r.get("name")
        scored.append({
            "clip_id": r["clip_id"], "player_id": r["player_id"], "name": r.get("name"),
            "player_name": pname, "club": r["club"], "file": r.get("file"),
            "caption": r["caption"], "media_type": r.get("media_type"),
            "video_url": r.get("video_url"), "poster_path": r.get("poster_path"),
            "score": round(_cos(qe, emb), 4)
        })
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Deterministic name gate: a name-like query ("Vini Jr", "Luis Diaz") resolves
    # straight to that player's gallery, ranked by embedding score. Descriptive
    # queries ("goalkeeper", "player in a red kit") match no name and fall through.
    names_by_player = {s["player_id"]: s["player_name"] or s["name"] for s in scored}
    named_pid = _name_resolve(q, names_by_player)
    if named_pid:
        clips = [s for s in scored if s["player_id"] == named_pid]
        clips.sort(key=lambda x: x["score"], reverse=True)
        p0 = clips[0]
        return {
            "query": q, "mode": "player",
            "player": {
                "player_id": named_pid, "name": p0["name"], "player_name": p0["player_name"],
                "club": p0["club"], "score": p0["score"], "match_margin": None
            },
            "clips": clips
        }

    # Deterministic CLUB gate: a club-name query ("Real Madrid", "Bayern") returns that
    # club's clips as a gallery. One player in the club -> identical UX to a name search;
    # several players -> a club-labelled gallery. Uses the structured `club` column.
    clubs = {s["club"] for s in scored if s.get("club")}
    club = _club_resolve(q, clubs)
    if club:
        clips = [s for s in scored if s["club"] == club]
        clips.sort(key=lambda x: x["score"], reverse=True)
        players = {s["player_id"] for s in clips}
        if len(players) == 1:
            p0 = clips[0]
            return {"query": q, "mode": "player",
                    "player": {"player_id": p0["player_id"], "name": p0["name"],
                               "player_name": p0["player_name"], "club": p0["club"],
                               "score": p0["score"], "match_margin": None},
                    "clips": clips}
        return {"query": q, "mode": "club",
                "club": {"name": club, "players": len(players), "count": len(clips)},
                "clips": clips}

    # scene / descriptive mode: ranked grid across players (semantic search only)
    return {"query": q, "mode": "scene", "player": None, "clips": scored[:k]}


def _read_clip_file(fn):
    # Accept either a bare filename (legacy) or a full /Volumes/... path (poster_path/video_url).
    path = fn if fn.startswith("/Volumes/") else f"{CLIPS_VOL}/{fn}"
    url = f"{_host()}/api/2.0/fs/files{path}"
    req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {_token()}"})
    return urllib.request.urlopen(req, timeout=90).read()


def _clip_file(clip_id):
    """Fetch clip file and schema info; return (file, media_type, video_url, poster_path)."""
    rows = query(f"SELECT file, media_type, video_url, poster_path FROM {CATALOG}.{SCHEMA}.clip_index "
                 f"WHERE clip_id='{clip_id.replace(chr(39),'')}'")
    if not rows:
        return None, None, None, None
    r = rows[0]
    return r.get("file"), r.get("media_type"), r.get("video_url"), r.get("poster_path")


def read_clip_image(clip_id):
    """Return (bytes, content_type) for a clip's still image. For a video clip,
    this serves its poster frame (real sampled frame from poster_path or {clip_id}.jpg),
    so the same endpoint feeds both <img> cards and <video poster=...>."""
    fn, media_type, video_url, poster_path = _clip_file(clip_id)
    if not fn and not poster_path:
        return None, None

    # Use poster_path if available (new schema), else derive from file
    if poster_path:
        fn = poster_path
    elif fn and fn.lower().endswith(".mp4"):
        fn = f"{clip_id.replace(chr(39),'')}.jpg"

    if not fn:
        return None, None
    data = _read_clip_file(fn)
    ct = "image/png" if fn.lower().endswith(".png") else "image/jpeg"
    return data, ct


def read_clip_frame(clip_id, idx):
    """Return JPEG bytes for a sampled video frame ({clip_id}_f{idx}.jpg in frames/).
    These are the actual decoded frames the FM vision model captioned — the multimodal proof."""
    fn = f"frames/{clip_id.replace(chr(39), '')}_f{int(idx)}.jpg"
    return _read_clip_file(fn)


def read_clip_video(clip_id):
    """Return (bytes, content_type) for a video clip's MP4 from the clips volume."""
    fn, media_type, video_url, poster_path = _clip_file(clip_id)

    # Use video_url if available (new schema), else check if file is .mp4
    if video_url:
        fn = video_url
    elif not fn or not fn.lower().endswith(".mp4"):
        return None, None

    return _read_clip_file(fn), "video/mp4"


# ---------- Genie Agent mode (blended answers with citations) ----------
def ask_genie(question: str, timeout=300):
    body = json.dumps({"input": [{"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": question}]}]}).encode()
    url = f"{_host()}/api/2.0/genie/agents/{GENIE_AGENT_ID}/responses"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    final, cid = None, None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            evt = json.loads(line[5:])
            if evt.get("type") == "response.completed":
                r = evt["response"]; cid = r.get("conversation_id")
                for it in r.get("output", []):
                    if it.get("type") == "message" and it.get("role") == "assistant":
                        final = "".join(c.get("text", "") for c in it.get("content", []))
            if evt.get("type") == "response.failed":
                return {"answer": None, "error": evt["response"].get("error")}
    return {"answer": final, "conversation_id": cid}

# Databricks notebook source
# MAGIC %md
# MAGIC # Ingest player VIDEOS into Scouting Clip Search (honest video-frame pipeline)
# MAGIC Real MP4s were staged into the clips volume by `scripts/fetch_videos.py`. Here we, per video:
# MAGIC 1. sample a few frames (ffmpeg, evenly spaced across the clip),
# MAGIC 2. caption **each frame** with FM vision (`databricks-gpt-5-mini`, same prompt as the image pipeline),
# MAGIC 3. embed the combined caption with the **same** embedder (`databricks-gte-large-en`),
# MAGIC 4. write one `clip_index` row per video (`file=*.mp4`), with a real sampled frame as poster.
# MAGIC
# MAGIC So "semantic search runs on video frames" is literally true — the vector is built from
# MAGIC captions of actual decoded frames, using the identical caption+embed endpoints as the images.

# COMMAND ----------

# MAGIC %pip install -q imageio-ffmpeg
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json, os, base64, subprocess, urllib.request
import imageio_ffmpeg
from pyspark.sql import functions as F, types as T

CATALOG, SCHEMA = "acme_sports", "demo"
VOL = f"/Volumes/{CATALOG}/{SCHEMA}/clips"
FRAMES_DIR = f"{VOL}/frames"
VISION_EP = "databricks-gpt-5-mini"
EMBED_EP = "databricks-gte-large-en"
N_FRAMES = 4  # frames sampled per video for the honest caption->embed pipeline

CAPTION_PROMPT = ("Describe this football match/video frame for a scouting clip-search index. "
    "Note kit/shirt colour and trim, any visible squad number, whether it is match action "
    "(dribble, shot, celebration) or a still, the setting (stadium/pitch), and any visible "
    "club/sponsor. 1-2 factual sentences. Do not guess the player's name.")

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
TOK = ctx.apiToken().get()
HOST = ctx.apiUrl().get()
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
os.makedirs(FRAMES_DIR, exist_ok=True)


def post(ep, body):
    req = urllib.request.Request(f"{HOST}/serving-endpoints/{ep}/invocations",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def caption_jpg(path):
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    d = post(VISION_EP, {"messages": [{"role": "user", "content": [
        {"type": "text", "text": CAPTION_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
        "max_tokens": 200})
    return d["choices"][0]["message"]["content"].strip()


def embed(text):
    return post(EMBED_EP, {"input": [text]})["data"][0]["embedding"]


def sample_frames(mp4_path, dur, clip_id, n=N_FRAMES):
    """Extract n evenly-spaced JPG frames with ffmpeg; persist to the volume; return paths."""
    dur = float(dur or 12)
    fracs = [(i + 1) / (n + 1) for i in range(n)]  # e.g. .2 .4 .6 .8
    paths = []
    for i, fr in enumerate(fracs, 1):
        t = round(dur * fr, 2)
        out = f"{FRAMES_DIR}/{clip_id}_f{i}.jpg"
        subprocess.run([FFMPEG, "-y", "-ss", str(t), "-i", mp4_path,
                        "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "3", out],
                       check=True, capture_output=True)
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            paths.append(out)
    return paths


# COMMAND ----------

manifest = json.load(open(f"{VOL}/video_manifest.json"))
print(f"{len(manifest)} videos staged in volume")

rows = []
for m in manifest:
    clip_id = m["clip_id"]
    mp4 = f"{VOL}/{m['file']}"
    frames = sample_frames(mp4, m.get("duration"), clip_id)
    caps = []
    for fp in frames:
        try:
            caps.append(caption_jpg(fp))
        except Exception as e:
            print(f"  {clip_id} frame caption failed: {str(e)[:80]}")
    # poster = a real sampled frame (mid-clip); overwrite the staged cover
    if frames:
        poster = frames[min(1, len(frames) - 1)]
        with open(poster, "rb") as s, open(f"{VOL}/{clip_id}.jpg", "wb") as d:
            d.write(s.read())
    combined = " ".join(caps) if caps else "Football video clip."
    doc = f"Player: {m['name']} ({m['club']}). {combined}"
    emb = embed(doc)
    caption_store = f"[video · {m.get('duration')}s · {len(frames)} frames sampled] {combined}"

    # New schema columns
    video_url_path = f"{VOL}/{m['file']}"
    poster_path = f"{VOL}/{clip_id}.jpg"

    rows.append({
        "clip_id": clip_id, "player_id": m["player_id"], "name": m["name"],
        "player_name": m["name"], "club": m["club"], "file": m["file"],
        "volume_path": m["volume_path"], "media_type": "video",
        "video_url": video_url_path, "poster_path": poster_path,
        "caption": caption_store, "embedding_json": json.dumps(emb),
        "model": f"{VISION_EP}+{EMBED_EP}"
    })
    print(f"indexed {clip_id:12} {m['name']:14} {len(frames)} frames -> cap='{combined[:70]}...'")

# COMMAND ----------

schema = T.StructType([T.StructField(c, T.StringType()) for c in
    ["clip_id", "player_id", "name", "player_name", "club", "file", "volume_path",
     "media_type", "video_url", "poster_path", "caption", "embedding_json", "model"]])
df = spark.createDataFrame(rows, schema).withColumn("indexed_at", F.current_timestamp())
df = df.select("clip_id", "player_id", "name", "player_name", "club", "file", "volume_path",
               "media_type", "video_url", "poster_path", "caption", "embedding_json", "model", "indexed_at")

# VIDEO-ONLY REBUILD: the clip index is now exclusively player highlight VIDEOS
# (no still images). Clear ALL prior rows (images + old video rows), then append.
players = sorted({m["player_id"] for m in manifest})
spark.sql(f"DELETE FROM {CATALOG}.{SCHEMA}.clip_index WHERE true")
df.write.mode("append").saveAsTable(f"{CATALOG}.{SCHEMA}.clip_index")

summary = {p: spark.sql(f"SELECT count(*) c FROM {CATALOG}.{SCHEMA}.clip_index WHERE player_id='{p}'").first()["c"]
           for p in players}
total = spark.sql(f"SELECT count(*) c FROM {CATALOG}.{SCHEMA}.clip_index").first()["c"]
imgs = spark.sql(f"SELECT count(*) c FROM {CATALOG}.{SCHEMA}.clip_index WHERE media_type <> 'video'").first()["c"]
print("per-player:", summary, "| total rows:", total, "| non-video rows:", imgs)
dbutils.notebook.exit(json.dumps({"video_rows": summary, "clip_index_total": total, "non_video": imgs}))

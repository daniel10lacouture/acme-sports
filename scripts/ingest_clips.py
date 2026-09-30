#!/usr/bin/env python3
"""Ingest clip images: upload to volume, FM vision caption, FM embed, store in clip_index.

Pipeline (identical shape works on video frames): image -> vision caption (gpt-5-mini
via image_url) -> embed 'Player: name (club). caption' (gte-large-en) -> clip_index row.
"""
import os, json, base64, subprocess, urllib.request, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbsql

PROFILE = "fe-vm-classic-stable-9cgeia"
HOST = "https://fevm-classic-stable-9cgeia.cloud.databricks.com"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "data", "clips")
VOL = "/Volumes/acme_sports/demo/clips"
VISION_EP = "databricks-gpt-5-mini"
EMBED_EP = "databricks-gte-large-en"

CAPTION_PROMPT = ("Describe this football player photo for a scouting image-search index. "
    "Note kit/shirt colour and trim, any visible squad number, hair, build, whether it is match "
    "action or a portrait, and any visible club/country crest or sponsor. 2-3 factual sentences. "
    "Do not guess the player's name.")


def token():
    return json.loads(subprocess.run(["databricks","auth","token","-p",PROFILE],
        capture_output=True,text=True,env=ENV).stdout)["access_token"]


def post(ep, body, tok):
    req = urllib.request.Request(f"{HOST}/serving-endpoints/{ep}/invocations",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def caption(path, tok):
    b64 = base64.b64encode(open(path,"rb").read()).decode()
    d = post(VISION_EP, {"messages":[{"role":"user","content":[
        {"type":"text","text":CAPTION_PROMPT},
        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],
        "max_tokens":300}, tok)
    return d["choices"][0]["message"]["content"].strip()


def embed(text, tok):
    d = post(EMBED_EP, {"input":[text]}, tok)
    return d["data"][0]["embedding"]


def up_volume(path, tok):
    fn = os.path.basename(path)
    url = f"{HOST}/api/2.0/fs/files{VOL}/{fn}?overwrite=true"
    req = urllib.request.Request(url, data=open(path,"rb").read(), method="PUT",
        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/octet-stream"})
    urllib.request.urlopen(req, timeout=120)
    return f"{VOL}/{fn}"


def esc(s): return s.replace("'", "''")


if __name__ == "__main__":
    tok = token()
    manifest = json.load(open(os.path.join(CLIPS, "manifest.json")))
    dbsql.run_sql("DELETE FROM acme_sports.demo.clip_index")
    for m in manifest:
        path = os.path.join(CLIPS, m["file"])
        vpath = up_volume(path, tok)
        cap = caption(path, tok)
        doc = f"Player: {m['name']} ({m['club']}). {cap}"
        emb = embed(doc, tok)
        dbsql.run_sql(
            "INSERT INTO acme_sports.demo.clip_index VALUES "
            f"('{esc(m['clip_id'])}','{esc(m['player_id'])}','{esc(m['name'])}','{esc(m['club'])}','{esc(m['file'])}',"
            f"'{esc(vpath)}','{esc(cap)}','{json.dumps(emb)}','{VISION_EP}+{EMBED_EP}',current_timestamp())")
        print(f"indexed {m['clip_id']:12} {m['name']:20} cap='{cap[:60]}...'")
    n = dbsql.run_sql("SELECT count(*) FROM acme_sports.demo.clip_index")["result"]["data_array"][0][0]
    print(f"\nclip_index rows: {n}")

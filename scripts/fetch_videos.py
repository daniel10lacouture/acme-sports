#!/usr/bin/env python3
"""Fetch REAL short player videos (TikTok via TikWM convert API) -> data/clips/,
upload MP4 + cover-poster + manifest to the UC clips volume.

Egress path (verified reachable, no API key):
  POST https://www.tikwm.com/api/  (url=<tiktok url>, hd=1) -> {data:{play,hdplay,cover,duration}}
  then GET the tiktokcdn `play` URL -> real video/mp4 bytes.

Frame-sampling -> FM vision caption -> embed happens on Databricks (ingest_videos_nb.py),
because this machine has no local video decoder and PyPI is firewalled. This script only
downloads the MP4s and stages them (+ manifest) in the volume for that notebook to read.

NOTE (demo-only): scraped social video is fine for THIS internal FEVM demo only
(ToS / watermark) — never customer-shippable.
"""
import os, json, subprocess, urllib.request, urllib.parse, time, sys

PROFILE = "fe-vm-classic-stable-9cgeia"
HOST = "https://fevm-classic-stable-9cgeia.cloud.databricks.com"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "data", "clips")
VOL = "/Volumes/acme_sports/demo/clips"
os.makedirs(CLIPS, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# (clip_id, player_id, name, club, tiktok_url)  -- 2-3 real clips per player.
VIDEOS = [
    # Vinicius Jr (new clip-search player, not in squad table)
    # NOTE: only content-verified clips are kept. Two earlier candidates were dropped
    # during curation because their sampled frames were NOT Vinicius and would read as
    # leakage in a "vini jr" search: @realmadrid/7488694228357254423 (Endrick #16) and
    # @vinijr/7672431853265112352 (a non-football personal vlog). Do not re-add without
    # re-verifying frame content.
    ("ext_vini_1", "ext_vini", "Vinicius Jr", "Real Madrid",
     "https://www.tiktok.com/@vinijr/video/7427647281102458145"),
    # Luis Diaz (existing clip-search player id ext_ldiaz; real clips are Bayern era)
    ("ext_ldiaz_1", "ext_ldiaz", "Luis Diaz", "Bayern Munich",
     "https://www.tiktok.com/@fcbayern/video/7541522998185020694"),
    ("ext_ldiaz_2", "ext_ldiaz", "Luis Diaz", "Bayern Munich",
     "https://www.tiktok.com/@dzenwira06/video/7539362530456554759"),
]


def token():
    return json.loads(subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
        capture_output=True, text=True, env=ENV).stdout)["access_token"]


def tikwm(url):
    data = urllib.parse.urlencode({"url": url, "hd": "1"}).encode()
    req = urllib.request.Request("https://www.tikwm.com/api/", data=data, method="POST",
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    d = json.load(urllib.request.urlopen(req, timeout=40))
    if d.get("code") != 0:
        raise RuntimeError(f"tikwm resolve failed: {d.get('msg')}")
    return d["data"]


def fetch(url, out, referer="https://www.tiktok.com/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    b = urllib.request.urlopen(req, timeout=90).read()
    open(out, "wb").write(b)
    return len(b)


def up_volume(local, remote_name, tok):
    url = f"{HOST}/api/2.0/fs/files{VOL}/{remote_name}?overwrite=true"
    req = urllib.request.Request(url, data=open(local, "rb").read(), method="PUT",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"})
    urllib.request.urlopen(req, timeout=180)
    return f"{VOL}/{remote_name}"


if __name__ == "__main__":
    tok = token()
    manifest = []
    for clip_id, pid, name, club, url in VIDEOS:
        try:
            d = tikwm(url)
        except Exception as e:
            print(f"!! {clip_id}: resolve failed: {e}")
            continue
        play = d.get("hdplay") or d.get("play")
        cover = d.get("origin_cover") or d.get("cover")
        dur = d.get("duration")
        mp4_name, jpg_name = f"{clip_id}.mp4", f"{clip_id}.jpg"
        mp4_path = os.path.join(CLIPS, mp4_name)
        jpg_path = os.path.join(CLIPS, jpg_name)
        try:
            nb = fetch(play, mp4_path)
            cb = fetch(cover, jpg_path) if cover else 0
        except Exception as e:
            print(f"!! {clip_id}: download failed: {e}")
            continue
        vpath = up_volume(mp4_path, mp4_name, tok)
        up_volume(jpg_path, jpg_name, tok)
        manifest.append({"clip_id": clip_id, "player_id": pid, "name": name, "club": club,
                         "file": mp4_name, "poster": jpg_name, "volume_path": vpath,
                         "duration": dur, "source_url": url, "bytes": nb})
        print(f"OK  {clip_id:12} {name:14} {dur}s  mp4={nb/1e6:.2f}MB cover={cb/1e3:.0f}KB @{url.split('@')[1].split('/')[0]}")
        time.sleep(0.4)

    mpath = os.path.join(CLIPS, "video_manifest.json")
    json.dump(manifest, open(mpath, "w"), indent=1)
    up_volume(mpath, "video_manifest.json", tok)
    byp = {}
    for m in manifest:
        byp[m["player_id"]] = byp.get(m["player_id"], 0) + 1
    print(f"\nStaged {len(manifest)} videos across {len(byp)} players: {byp}")
    print(f"manifest -> {VOL}/video_manifest.json")

#!/usr/bin/env python3
"""Fetch >=8 REAL short highlight videos per player (Vinicius Jr, Raphinha, Luis Diaz,
Haaland) via the TikWM resolve-by-id API, stage MP4 + poster + manifest into the UC clips
volume for the honest frame-sample->caption->embed pipeline (notebooks/ingest_videos.py).

Sources: candidate ids harvested by scripts/harvest_ids.py (urlebird hashtag pages) plus a
few hand-verified pinned clips. Each candidate is resolved, sanity-filtered (duration, size,
cross-player title exclusion), downloaded and uploaded. DEMO-ONLY (scraped social video).
"""
import os, json, subprocess, urllib.request, urllib.parse, time, re

PROFILE = "fe-vm-classic-stable-9cgeia"
HOST = "https://fevm-classic-stable-9cgeia.cloud.databricks.com"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIPS = os.path.join(ROOT, "data", "clips")
VOL = "/Volumes/acme_sports/demo/clips"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
TARGET = 10          # download up to this many per player (>=8 goal, margin for ingest)
os.makedirs(CLIPS, exist_ok=True)

META = {
    "ext_vini":    ("Vinicius Jr", "Real Madrid"),
    "ext_raphinha": ("Raphinha", "Barcelona"),
    "ext_ldiaz":   ("Luis Diaz", "Bayern Munich"),
    "ext_haaland": ("Erling Haaland", "Manchester City"),
}
# hand-verified clips to place first (content confirmed in prior curation)
PINNED = {
    "ext_vini":  ["7427647281102458145"],
    "ext_ldiaz": ["7541522998185020694", "7539362530456554759"],
}
# distinctive tokens; a candidate is rejected if its title carries ANOTHER player's token
DISTINCT = {
    "ext_vini": ["vinic", "vini jr", "vinijr"],
    "ext_raphinha": ["raphinha"],
    "ext_ldiaz": ["luis diaz", "luisdiaz", "lucho"],
    "ext_haaland": ["haaland"],
}
# highlight-bias scoring: reject off-pitch noise (haircut memes, FIFA, transfer talk,
# family/reaction clips), prefer real match-action titles. Keeps the gallery on-brand
# as *scouting film* rather than social miscellany.
EXCLUDE = ["haircut", "buzz cut", "buzzcut", " hair", "hairstyle", "ishowspeed", "fifa",
    "fc26", "fc 26", "efootball", "transfer", "rumor", "rumour", " deal", "afford", "will sign",
    "stays at", "return to liverpool", " son", "filho", "hijo", "gamper", "#react", "reaction",
    "meme", "crashed out", "followers", "haalandoso", "buzz", "yall only", "yall", "return🔥",
    # multilingual off-pitch noise (lifestyle/hair/relationship/cooking/looks)
    "corte", "love story", "isabel", "girlfriend", "novia", "wife", "esposa", "cosinando",
    "cocinando", "belleza", "living his best", "x lamine", "lamine yamal", "vs ronaldo",
    "vs messi", "who deserves", "best life", "story of"]
PREFER = ["goal", "golazo", " gol ", "hat-trick", "hattrick", "hat trick", "assist", "skill",
    "dribble", "nutmeg", "wonder", "screamer", "free kick", "freekick", "magic", "highlight",
    "today vs", " vs ", " v ", "debut", "world class", "worldclass", "brace", "finish", "run"]


def hl_score(title):
    t = " " + (title or "").lower() + " "
    if any(x in t for x in EXCLUDE):
        return -100
    return sum(2 for x in PREFER if x in t)


def token():
    return json.loads(subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
        capture_output=True, text=True, env=ENV).stdout)["access_token"]


def resolve(vid):
    data = urllib.parse.urlencode({"url": f"https://www.tiktok.com/@x/video/{vid}", "hd": "1"}).encode()
    req = urllib.request.Request("https://www.tikwm.com/api/", data=data, method="POST",
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"})
    d = json.load(urllib.request.urlopen(req, timeout=40))
    if d.get("code") != 0:
        raise RuntimeError(d.get("msg"))
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


def cross_reject(pid, title):
    t = (title or "").lower()
    for other, toks in DISTINCT.items():
        if other == pid:
            continue
        if any(tok in t for tok in toks):
            return True
    return False


def try_clip(pid, vid, seen_authors):
    d = resolve(vid)
    title = d.get("title") or ""
    author = (d.get("author") or {}).get("unique_id", "")
    dur = int(d.get("duration") or 0)
    if not (5 <= dur <= 80):
        return None, f"dur {dur}s"
    if cross_reject(pid, title):
        return None, "cross-player title"
    if hl_score(title) < 0:
        return None, "off-topic (excluded)"
    play = d.get("hdplay") or d.get("play")
    cover = d.get("origin_cover") or d.get("cover")
    if not play or not cover:
        return None, "no media url"
    return {"play": play, "cover": cover, "dur": dur, "title": title[:60],
            "author": author, "video_id": vid}, "ok"


if __name__ == "__main__":
    cands = json.load(open(os.path.join(CLIPS, "candidates.json")))
    tok = token()
    manifest = []
    report = {}
    for pid, (name, club) in META.items():
        ids = list(PINNED.get(pid, []))
        # rank candidates by highlight score (drop clearly off-topic ones up front)
        ranked = sorted((c for c in cands.get(pid, []) if hl_score(c.get("title", "")) >= 0),
                        key=lambda c: hl_score(c.get("title", "")), reverse=True)
        for c in ranked:
            if c["video_id"] not in ids:
                ids.append(c["video_id"])
        got = 0
        idx = 0
        authors = {}
        for vid in ids:
            if got >= TARGET:
                break
            try:
                info, why = try_clip(pid, vid, authors)
            except Exception as e:
                time.sleep(0.6)
                continue
            if not info:
                continue
            # light author de-dup: allow at most 3 from a single account for variety
            if authors.get(info["author"], 0) >= 3:
                continue
            idx += 1
            clip_id = f"{pid}_{idx}"
            mp4_name, jpg_name = f"{clip_id}.mp4", f"{clip_id}.jpg"
            mp4_path = os.path.join(CLIPS, mp4_name)
            jpg_path = os.path.join(CLIPS, jpg_name)
            try:
                nb = fetch(info["play"], mp4_path)
                if nb < 150_000 or nb > 30_000_000:
                    print(f"  skip {clip_id} size {nb/1e6:.1f}MB")
                    idx -= 1
                    continue
                fetch(info["cover"], jpg_path)
            except Exception as e:
                print(f"  !! {clip_id} download failed: {str(e)[:70]}")
                idx -= 1
                continue
            vpath = up_volume(mp4_path, mp4_name, tok)
            up_volume(jpg_path, jpg_name, tok)
            manifest.append({"clip_id": clip_id, "player_id": pid, "name": name, "club": club,
                             "file": mp4_name, "poster": jpg_name, "volume_path": vpath,
                             "duration": info["dur"], "source_id": vid, "bytes": nb})
            authors[info["author"]] = authors.get(info["author"], 0) + 1
            got += 1
            print(f"OK  {clip_id:16} {name:14} {info['dur']:>3}s {nb/1e6:5.2f}MB @{info['author'][:20]:20} :: {info['title']}")
            time.sleep(0.6)
        report[pid] = got
        print(f"== {pid}: {got} clips staged\n")

    json.dump(manifest, open(os.path.join(CLIPS, "video_manifest.json"), "w"), indent=1, ensure_ascii=False)
    up_volume(os.path.join(CLIPS, "video_manifest.json"), "video_manifest.json", tok)
    print("STAGED:", report, "| total", len(manifest))
    print(f"manifest -> {VOL}/video_manifest.json")

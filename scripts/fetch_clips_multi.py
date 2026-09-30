#!/usr/bin/env python3
"""Fetch MULTIPLE images per player via Wikimedia Commons search -> data/clips/.
Builds galleries (clip_id = {player_id}_{n}). Keeps existing singles for others."""
import os, json, urllib.request, urllib.parse, time, re

UA = "AcmeSportsDemo/1.0 (daniel.lacouture@databricks.com)"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clips")
os.makedirs(OUT, exist_ok=True)

# priority players get galleries (search term, target count)
GALLERY = [
 ("ext_ldiaz", "Luis Díaz",       "Bayern Munich",   "Luis Díaz footballer", 4),
 ("ext_rodri", "Rodri",           "Manchester City", "Rodri footballer Manchester City", 4),
 ("p_saka",    "Bukayo Saka",     "Arsenal",         "Bukayo Saka", 4),
 ("p_barcola", "Bradley Barcola", "Paris SG",        "Bradley Barcola", 4),
 ("p_roque",   "Vitor Roque",     "Palmeiras",       "Vitor Roque footballer", 3),
 ("p_saliba",  "William Saliba",  "Arsenal",         "William Saliba", 3),
]
# these keep their existing single image (from fetch_clips.py)
SINGLES = [
 ("p_rice","Declan Rice","Arsenal"),("p_odegaard","Martin Ødegaard","Arsenal"),
 ("p_raya","David Raya","Arsenal"),("p_olise","Michael Olise","Bayern Munich"),
 ("p_alvarez","Julián Álvarez","Atlético Madrid"),("p_tonali","Sandro Tonali","Newcastle"),
]

SKIP = re.compile(r"logo|crest|badge|\.svg|icon|signature|stadium|map", re.I)


def commons_images(term, want):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrsearch": term, "gsrlimit": "20",
        "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "500"})
    url = "https://commons.wikimedia.org/w/api.php?" + q
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30))
    pages = list((d.get("query", {}).get("pages", {}) or {}).values())
    pages.sort(key=lambda p: p.get("index", 999))
    out = []
    for p in pages:
        title = p.get("title", "")
        ii = (p.get("imageinfo") or [{}])[0]
        mime, thumb, w = ii.get("mime", ""), ii.get("thumburl"), ii.get("thumbwidth", 0)
        if mime not in ("image/jpeg", "image/png") or not thumb or SKIP.search(title):
            continue
        out.append((thumb, mime))
        if len(out) >= want:
            break
    return out


manifest = []
for pid, name, club, term, want in GALLERY:
    imgs = commons_images(term, want)
    n = 0
    for thumb, mime in imgs:
        try:
            data = urllib.request.urlopen(urllib.request.Request(thumb, headers={"User-Agent": UA}), timeout=25).read()
            if len(data) < 4000:
                continue
            n += 1
            ext = ".png" if mime == "image/png" else ".jpg"
            fn = f"{pid}_{n}{ext}"
            open(os.path.join(OUT, fn), "wb").write(data)
            manifest.append({"clip_id": f"{pid}_{n}", "player_id": pid, "name": name, "club": club,
                             "file": fn, "bytes": len(data)})
        except Exception as e:
            print(f"  .. {pid} img failed: {str(e)[:50]}")
        time.sleep(0.5)
    print(f"{pid:12} {name:18} -> {n} images")
    time.sleep(1.0)

# keep singles (reuse files already downloaded by fetch_clips.py)
for pid, name, club in SINGLES:
    f = f"{pid}.jpg"
    if os.path.exists(os.path.join(OUT, f)):
        manifest.append({"clip_id": f"{pid}_1", "player_id": pid, "name": name, "club": club,
                         "file": f, "bytes": os.path.getsize(os.path.join(OUT, f))})
        print(f"{pid:12} {name:18} -> 1 image (existing single)")

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
byp = {}
for m in manifest:
    byp[m["player_id"]] = byp.get(m["player_id"], 0) + 1
print(f"\nTotal {len(manifest)} images across {len(byp)} players: {byp}")

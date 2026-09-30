#!/usr/bin/env python3
"""Download ~12 player photos via the Wikipedia REST summary API -> data/clips/."""
import os, json, urllib.request, urllib.parse, time

UA = "AcmeSportsDemo/1.0 (daniel.lacouture@databricks.com)"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clips")
os.makedirs(OUT, exist_ok=True)

# (clip_id, display name, club, [candidate Wikipedia titles])
PLAYERS = [
 ("ext_ldiaz",  "Luis Díaz",        "Bayern Munich",  ["Luis Díaz", "Luis Díaz (footballer, born 1997)"]),
 ("ext_rodri",  "Rodri",            "Manchester City", ["Rodri (footballer, born 1996)", "Rodri"]),
 ("p_saka",     "Bukayo Saka",      "Arsenal",         ["Bukayo Saka"]),
 ("p_saliba",   "William Saliba",   "Arsenal",         ["William Saliba"]),
 ("p_rice",     "Declan Rice",      "Arsenal",         ["Declan Rice"]),
 ("p_odegaard", "Martin Ødegaard",  "Arsenal",         ["Martin Ødegaard"]),
 ("p_raya",     "David Raya",       "Arsenal",         ["David Raya"]),
 ("p_barcola",  "Bradley Barcola",  "Paris SG",        ["Bradley Barcola"]),
 ("p_olise",    "Michael Olise",    "Bayern Munich",   ["Michael Olise"]),
 ("p_roque",    "Vitor Roque",      "Palmeiras",       ["Vitor Roque", "Vitor Roque (footballer, born 2005)"]),
 ("p_alvarez",  "Julián Álvarez",   "Atlético Madrid", ["Julián Álvarez (footballer)", "Julián Álvarez"]),
 ("p_tonali",   "Sandro Tonali",    "Newcastle",       ["Sandro Tonali"]),
]


def summary(title):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=20))


def img_url(title):
    d = summary(title)
    src = (d.get("originalimage") or {}).get("source") or (d.get("thumbnail") or {}).get("source")
    if not src:
        return None
    # prefer a ~500px thumb for consistency
    if "/thumb/" in src and "px-" in src:
        import re
        src = re.sub(r"/(\d+)px-", "/500px-", src)
    return src.split("?")[0]


manifest = []
for cid, name, club, titles in PLAYERS:
    got = False
    for t in titles:
        try:
            u = img_url(t)
            if not u:
                continue
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=25).read()
            if len(data) < 3000:  # too small / error page
                continue
            ext = ".jpg" if u.lower().endswith((".jpg", ".jpeg")) else (".png" if u.lower().endswith(".png") else ".jpg")
            fn = os.path.join(OUT, cid + ext)
            open(fn, "wb").write(data)
            manifest.append({"clip_id": cid, "name": name, "club": club, "file": os.path.basename(fn),
                             "source_title": t, "bytes": len(data)})
            print(f"OK  {cid:12} {name:20} <- {t}  ({len(data)//1024} KB)")
            got = True
            break
        except Exception as e:
            print(f"..  {cid} try '{t}' failed: {str(e)[:60]}")
        time.sleep(0.3)
    if not got:
        print(f"XX  {cid} {name}: NO IMAGE")

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print(f"\nDownloaded {len(manifest)}/{len(PLAYERS)} -> {OUT}")

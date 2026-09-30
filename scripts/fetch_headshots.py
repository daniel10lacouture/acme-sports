#!/usr/bin/env python3
"""Fetch candidate player HEADSHOTS from Wikimedia Commons -> data/headshots_candidates/.

Correctness-first: the Commons file title is the identity anchor. We keep ONLY files
whose title STARTS WITH the player's own name (after 'File:'), which rejects the
wrong-person leaks we saw before (e.g. 'File:Jose Luis Rodriguez Bukayo Saka ...' or
'File:Gideon Mensah Bukayo Saka ...' — those do NOT start with Saka's name).

We prefer PORTRAIT orientation (head-and-shoulders) and larger files. Downloads the
top few per player for human + FM-vision verification (fetch is not the final gate).
"""
import os, json, urllib.request, urllib.parse, time, re, unicodedata

UA = "AcmeSportsDemo/1.0 (you@example.com)"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "headshots_candidates")
os.makedirs(OUT, exist_ok=True)

# player_id, commons search term, [accepted normalized name-prefixes]
PLAYERS = [
 ("p_saka",     "Bukayo Saka",                 ["bukayo saka"]),
 ("p_rice",     "Declan Rice",                 ["declan rice"]),
 ("p_saliba",   "William Saliba",              ["william saliba"]),
 ("p_odegaard", "Martin Ødegaard",             ["martin odegaard", "martin oedegaard"]),
 ("p_gabriel",  "Gabriel Magalhães Arsenal",   ["gabriel magalhaes", "gabriel dos santos", "gabriel (footballer"]),
 ("p_raya",     "David Raya",                  ["david raya"]),
 ("p_white",    "Ben White footballer",        ["ben white"]),
 ("p_timber",   "Jurriën Timber",              ["jurrien timber"]),
 ("p_norgaard", "Christian Nørgaard",          ["christian norgaard", "christian noergaard"]),
 ("p_mosquera", "Cristian Mosquera footballer",["cristian mosquera"]),
 ("p_alvarez",  "Julián Álvarez footballer",   ["julian alvarez"]),
 ("p_olise",    "Michael Olise",               ["michael olise"]),
 ("p_barcola",  "Bradley Barcola",             ["bradley barcola"]),
 ("p_tonali",   "Sandro Tonali",               ["sandro tonali"]),
 ("p_rogers",   "Morgan Rogers footballer",    ["morgan rogers"]),
 ("p_roque",    "Vitor Roque",                 ["vitor roque"]),
 ("p_brown",    "Nathaniel Brown footballer",  ["nathaniel brown"]),
 # academy — try, but expect failures -> placeholder
 ("p_dowman",   "Max Dowman",                  ["max dowman"]),
 ("p_annous",   "Andre Annous",                ["andre annous"]),
 ("p_clarke",   "Brayden Clarke footballer",   ["brayden clarke"]),
]

SKIP = re.compile(r"logo|crest|badge|\.svg|icon|signature|stadium|map|celebrat", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def commons(term, prefixes):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrsearch": term, "gsrlimit": "30",
        "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "600"})
    url = "https://commons.wikimedia.org/w/api.php?" + q
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30))
    pages = list((d.get("query", {}).get("pages", {}) or {}).values())
    pages.sort(key=lambda p: p.get("index", 999))
    cands = []
    for p in pages:
        title = p.get("title", "")
        base = norm(re.sub(r"\.(jpg|jpeg|png)$", "", title.replace("File:", ""), flags=re.I))
        ii = (p.get("imageinfo") or [{}])[0]
        mime, thumb = ii.get("mime", ""), ii.get("thumburl")
        w, h = ii.get("thumbwidth", 0), ii.get("thumbheight", 0)
        if mime not in ("image/jpeg", "image/png") or not thumb or SKIP.search(title):
            continue
        # IDENTITY GATE: title must START WITH the player's own name.
        if not any(base.startswith(pref) for pref in prefixes):
            continue
        portrait = h >= w  # head-and-shoulders bias
        score = (2 if portrait else 0) + min(w * h, 600 * 900) / (600 * 900)
        cands.append({"title": title, "thumb": thumb, "mime": mime, "w": w, "h": h,
                      "portrait": portrait, "score": round(score, 3)})
    cands.sort(key=lambda c: -c["score"])
    return cands


manifest = {}
for pid, term, prefixes in PLAYERS:
    try:
        cands = commons(term, prefixes)
    except Exception as e:
        print(f"{pid:12} SEARCH FAILED: {str(e)[:60]}"); cands = []
    saved = []
    for i, c in enumerate(cands[:3], 1):
        try:
            data = urllib.request.urlopen(urllib.request.Request(c["thumb"], headers={"User-Agent": UA}), timeout=25).read()
            if len(data) < 4000:
                continue
            fn = f"{pid}_{i}.jpg"
            open(os.path.join(OUT, fn), "wb").write(data)
            saved.append({"file": fn, "title": c["title"], "w": c["w"], "h": c["h"],
                          "portrait": c["portrait"], "bytes": len(data)})
        except Exception as e:
            print(f"  .. {pid} dl failed: {str(e)[:40]}")
        time.sleep(0.4)
    manifest[pid] = saved
    tag = "OK " if saved else "-- none (placeholder)"
    print(f"{pid:12} {term:28} -> {len(saved)} candidate(s) {tag}")
    time.sleep(0.8)

json.dump(manifest, open(os.path.join(OUT, "candidates.json"), "w"), indent=1)
n_ok = sum(1 for v in manifest.values() if v)
print(f"\n{n_ok}/{len(PLAYERS)} players have >=1 title-gated candidate. Now VISUALLY VERIFY each.")

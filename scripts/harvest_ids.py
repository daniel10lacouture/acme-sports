#!/usr/bin/env python3
"""Harvest candidate TikTok video IDs per player from urlebird hashtag pages
(+ AJAX load-more pagination), capturing the slug title and author handle so we can
filter to clips that plausibly show the right player. Output: data/clips/candidates.json

This is a DEMO-ONLY sourcing helper (scraped social video, internal FEVM demo). The
actual frame-sample -> vision-caption -> embed happens on Databricks (ingest_videos.py).
"""
import urllib.request, urllib.parse, re, json, time, os, html

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "clips", "candidates.json")

# player_id -> (hashtags to scrape, name tokens that should appear in title OR author)
PLAYERS = {
    "ext_vini":   (["viniciusjr", "viniciusjunior", "vinicius", "vinijr"],
                   ["vini", "vinicius"]),
    "ext_raphinha": (["raphinha", "raphinhafcb", "raphinha11"],
                     ["raphinha"]),
    "ext_ldiaz":  (["luisdiaz", "luisdiaz7", "luchodiaz", "luisdiazbayern"],
                   ["luis diaz", "luisdiaz", "lucho", "diaz"]),
    "ext_haaland": (["haaland", "erlinghaaland", "haaland9", "haalandgoal", "haalandgoals",
                     "haalandedit", "haalandskills", "erlinghaalandgoals"],
                    ["haaland"]),
}
MAX_PAGES = 5  # ajax pages per hashtag


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")


def ajax(attrs):
    payload = {k: attrs.get(k, "") for k in ["hash", "id", "cursor", "lang", "page", "x"]}
    body = urllib.parse.urlencode({"action": "hash", "data": json.dumps(payload)}).encode()
    req = urllib.request.Request("https://urlebird.com/ajax/", data=body, method="POST",
        headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest",
                 "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")


def parse_items(fragment):
    """Return [(video_id, title, author_handle)] from a urlebird HTML fragment."""
    out = []
    # each item block: author link + video link (slug ends with -<id>)
    for m in re.finditer(r'href="https://urlebird\.com/video/([^"/]+?)-(\d{15,25})/"', fragment):
        slug, vid = m.group(1), m.group(2)
        title = html.unescape(slug.replace("-", " "))
        # author: nearest preceding /user/<handle>/
        pre = fragment[:m.start()]
        am = None
        for am in re.finditer(r'urlebird\.com/user/([^"/]+)/', pre):
            pass
        author = am.group(1) if am else ""
        out.append((vid, title, author))
    return out


def harvest_tag(tag):
    items = {}
    try:
        h = get(f"https://urlebird.com/hash/{tag}/")
    except Exception as e:
        print(f"    tag {tag}: page load err {e}")
        return items
    for vid, title, author in parse_items(h):
        items[vid] = (title, author)
    i = h.find("hash_load_more")
    if i < 0:
        return items
    btn = h[h.rfind("<button", 0, i):i + 400]
    attrs = dict(re.findall(r'data-([a-z]+)="([^"]*)"', btn))
    for _ in range(MAX_PAGES):
        try:
            d = json.loads(ajax(attrs))
        except Exception as e:
            print(f"    tag {tag}: ajax err {e}")
            break
        frag = d.get("thumbs") or ""
        for vid, title, author in parse_items(frag):
            items.setdefault(vid, (title, author))
        for k in ["cursor", "page", "x", "id"]:
            if d.get(k) is not None:
                attrs[k] = str(d[k])
        if not d.get("has_more") or not frag:
            break
        time.sleep(1.5)
    return items


def keep(title, author, tokens):
    t = title.lower()
    a = author.lower()
    return any(tok in t or tok.replace(" ", "") in a or tok in a for tok in tokens)


if __name__ == "__main__":
    result = {}
    for pid, (tags, tokens) in PLAYERS.items():
        pool = {}
        for tag in tags:
            got = harvest_tag(tag)
            pool.update(got)
            print(f"  #{tag}: {len(got)} items (pool now {len(pool)})")
            time.sleep(1)
        # filter to plausible player clips
        cands = [{"video_id": vid, "title": title, "author": author}
                 for vid, (title, author) in pool.items() if keep(title, author, tokens)]
        result[pid] = cands
        print(f"== {pid}: {len(cands)} filtered candidates (from {len(pool)} raw)\n")
    json.dump(result, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: " + ", ".join(f"{k}={len(v)}" for k, v in result.items()))

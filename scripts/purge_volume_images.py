#!/usr/bin/env python3
"""Delete leftover STILL-IMAGE files from the clips volume so it holds only the
player highlight videos + their (real sampled-frame) posters + the manifest + frames/.
Keep-set is derived from clip_index (video_url + poster_path). DEMO cleanup."""
import os, json, subprocess, urllib.request, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbsql

PROFILE = "fe-vm-classic-stable-9cgeia"
HOST = "https://fevm-classic-stable-9cgeia.cloud.databricks.com"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
VOL = "/Volumes/acme_sports/demo/clips"


def token():
    return json.loads(subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
        capture_output=True, text=True, env=ENV).stdout)["access_token"]


def listing(tok):
    url = f"{HOST}/api/2.0/fs/directories{VOL}"
    req = urllib.request.Request(url, method="GET", headers={"Authorization": f"Bearer {tok}"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return [(c["name"], c.get("is_directory", False)) for c in d.get("contents", [])]


def delete(name, tok):
    url = f"{HOST}/api/2.0/fs/files{VOL}/{name}"
    req = urllib.request.Request(url, method="DELETE", headers={"Authorization": f"Bearer {tok}"})
    urllib.request.urlopen(req, timeout=60)


if __name__ == "__main__":
    rows = dbsql.query_rows(f"SELECT video_url, poster_path FROM acme_sports.demo.clip_index")
    keep = set()
    for r in rows:
        for p in (r.get("video_url"), r.get("poster_path")):
            if p:
                keep.add(os.path.basename(p))
    keep |= {"video_manifest.json", "frames"}  # frames dir + live manifest
    tok = token()
    deleted, kept = [], []
    for name, is_dir in listing(tok):
        if is_dir or name in keep or not (name.lower().endswith((".jpg", ".jpeg", ".png"))
                                          or name == "manifest.json"):
            kept.append(name)
            continue
        try:
            delete(name, tok)
            deleted.append(name)
        except Exception as e:
            print(f"  !! delete {name} failed: {str(e)[:80]}")
    print(f"deleted {len(deleted)} image/stale files:")
    for d in deleted:
        print("  -", d)
    print(f"\nkept {len(kept)} files (videos, posters, manifest, frames)")

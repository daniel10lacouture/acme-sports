#!/usr/bin/env python3
"""Regenerate the mock clip-search fixtures from LIVE resolver output.

Calls the real app resolver (app/server/dbx.py search_clips) against the live
warehouse for the name queries the mock maps to fixtures, then writes the JSON
to mock/fixtures/. The returned clip objects already exclude embeddings, so the
fixture mirrors exactly what the deployed API returns. Run from the repo root:

  DATABRICKS_AUTH_STORAGE=plaintext python3 scripts/gen_clip_fixtures.py
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ.setdefault("DATABRICKS_PROFILE", "YOUR_PROFILE")

from server import dbx  # noqa: E402

FIX = os.path.join(ROOT, "mock", "fixtures")

# (query, fixture filename) — must match mock_server.clip_fixture() routing.
JOBS = [
    ("vini jr", "clip_vini_jr.json"),
    ("luis diaz", "clip_luis_diaz.json"),
]

for q, fname in JOBS:
    res = dbx.search_clips(q)
    # scrub any accidental embedding field just in case
    for c in res.get("clips", []):
        c.pop("embedding_json", None)
    path = os.path.join(FIX, fname)
    json.dump(res, open(path, "w"), indent=1, ensure_ascii=False)
    clips = res.get("clips", [])
    p = res.get("player") or {}
    print(f"{q:12} -> mode={res.get('mode'):6} player={p.get('player_name') or p.get('name')} "
          f"clips={len(clips)} ids={[c['clip_id'] for c in clips]} -> {fname}")

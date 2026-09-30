#!/usr/bin/env python3
"""Discover the correct field name(s) for a volume item under data_sources.volumes."""
import json, subprocess, os

PROFILE = "YOUR_PROFILE"
SPACE_ID = "YOUR_GENIE_SPACE_ID"
VOL = "acme_sports.demo.documents"
VOL_PATH = "/Volumes/acme_sports/demo/documents"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}


def get_space():
    r = subprocess.run(["databricks", "genie", "get-space", SPACE_ID,
                        "--include-serialized-space", "-p", PROFILE, "-o", "json"],
                       capture_output=True, text=True, env=ENV)
    return json.loads(r.stdout)


def update(serialized, etag):
    r = subprocess.run(["databricks", "genie", "update-space", SPACE_ID,
                        "--serialized-space", serialized, "--etag", etag,
                        "-p", PROFILE, "-o", "json"],
                       capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


item_candidates = [
    {"volume": VOL},
    {"volume_name": VOL},
    {"full_name": VOL},
    {"volume_full_name": VOL},
    {"path": VOL_PATH},
    {"volume_path": VOL_PATH},
    {"catalog_name": "acme_sports", "schema_name": "demo", "volume_name": "documents"},
    {"uc_volume": VOL},
    {"volume_identifier": VOL},
]

for item in item_candidates:
    d = get_space()
    etag = d.get("etag", "")
    s = json.loads(d["serialized_space"])
    s["data_sources"].pop("volumes", None)
    s["data_sources"]["volumes"] = [item]
    rc, out, err = update(json.dumps(s), etag)
    if rc == 0:
        d2 = get_space()
        s2 = json.loads(d2["serialized_space"])
        print(f"[SUCCESS] item fields {list(item.keys())} ACCEPTED")
        print("   persisted:", json.dumps(s2["data_sources"].get("volumes")))
        break
    else:
        msg = err.strip().replace("Error: Invalid serialized_space:", "").strip()
        print(f"[rej] {list(item.keys())}: {msg[:120]}")

# cleanup
d = get_space()
s = json.loads(d["serialized_space"])
s["data_sources"].pop("volumes", None)
update(json.dumps(s), d.get("etag", ""))

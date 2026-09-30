#!/usr/bin/env python3
"""Empirically probe whether a UC volume can be attached to a Genie space via API.
Tries several candidate serialized_space shapes; after each update, reads the space
back and reports whether the volume reference survived."""
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


def base_space(d):
    return json.loads(d["serialized_space"])


def update(serialized, etag):
    r = subprocess.run(["databricks", "genie", "update-space", SPACE_ID,
                        "--serialized-space", serialized, "--etag", etag,
                        "-p", PROFILE, "-o", "json"],
                       capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


# candidate shapes to inject into data_sources (and one top-level)
candidates = [
    ("data_sources.volumes[{identifier}]",
     lambda s: s["data_sources"].__setitem__("volumes", [{"identifier": VOL}])),
    ("data_sources.volumes[{name,path}]",
     lambda s: s["data_sources"].__setitem__("volumes", [{"name": VOL, "path": VOL_PATH}])),
    ("data_sources.files[{identifier}]",
     lambda s: s["data_sources"].__setitem__("files", [{"identifier": VOL}])),
    ("data_sources.unstructured[{volume}]",
     lambda s: s["data_sources"].__setitem__("unstructured", [{"volume": VOL}])),
    ("data_sources.documents[{path}]",
     lambda s: s["data_sources"].__setitem__("documents", [{"path": VOL_PATH}])),
]

VOL_KEYS = ["volumes", "files", "unstructured", "documents"]

for label, mutate in candidates:
    d = get_space()
    etag = d.get("etag", "")
    s = base_space(d)
    # strip any prior probe keys
    for k in VOL_KEYS:
        s["data_sources"].pop(k, None)
    mutate(s)
    rc, out, err = update(json.dumps(s), etag)
    # read back
    d2 = get_space()
    s2 = base_space(d2)
    survived = {k: s2["data_sources"].get(k) for k in VOL_KEYS if k in s2["data_sources"]}
    status = "ERR" if rc != 0 else "ok"
    print(f"[{status}] {label}")
    if rc != 0:
        print("     stderr:", err.strip()[:180])
    print("     persisted volume-ish keys:", survived if survived else "NONE")
    print()

# cleanup: remove any probe keys, restore clean tables-only data_sources
d = get_space()
etag = d.get("etag", "")
s = base_space(d)
for k in VOL_KEYS:
    s["data_sources"].pop(k, None)
rc, out, err = update(json.dumps(s), etag)
print("cleanup rc:", rc)

#!/usr/bin/env python3
"""Create the 'Acme Scout' Genie space programmatically from our tuning files."""
import json, subprocess, os, uuid, sys

PROFILE = "YOUR_PROFILE"
WAREHOUSE_ID = "YOUR_WAREHOUSE_ID"
PARENT = "/Users/you@example.com"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def newid():
    return uuid.uuid4().hex


def build_serialized_space(include_volume=False):
    instructions = open(os.path.join(ROOT, "genie_instructions.md")).read().strip()
    questions = [q.strip() for q in
                 open(os.path.join(ROOT, "genie_sample_questions.txt")).read().splitlines()
                 if q.strip()]
    data_sources = {"tables": [{"identifier": "acme_sports.demo.players"}]}
    if include_volume:
        # speculative shape — verified against API after create
        data_sources["volumes"] = [{"identifier": "acme_sports.demo.documents"}]
    space = {
        "version": 2,
        "config": {
            "sample_questions": [{"id": newid(), "question": [q]} for q in questions]
        },
        "data_sources": data_sources,
        "instructions": {
            "text_instructions": [{"id": newid(), "content": [instructions]}]
        },
    }
    return json.dumps(space)


def create(serialized):
    cmd = ["databricks", "genie", "create-space", WAREHOUSE_ID, serialized,
           "--title", "Acme Scout",
           "--description", "Conversational scout-reporting agent over Acme Sports squad data + contract/scout documents.",
           "--parent-path", PARENT,
           "-p", PROFILE, "-o", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        print("CREATE FAILED:\n", r.stderr, r.stdout)
        sys.exit(1)
    return json.loads(r.stdout)


if __name__ == "__main__":
    ss = build_serialized_space(include_volume=False)
    print("serialized_space to submit:")
    print(json.dumps(json.loads(ss), indent=1)[:1200])
    resp = create(ss)
    print("\n=== CREATED ===")
    print("space_id:", resp.get("space_id"))
    open(os.path.join(ROOT, ".space_id"), "w").write(resp.get("space_id", ""))
    print("(saved to .space_id)")

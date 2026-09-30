#!/usr/bin/env python3
"""Additively attach uploaded_docs (live-queried Delta table of app-uploaded contracts +
voice notes) to the Acme Scout Genie space, plus an instruction telling the agent to
prefer it for anything 'just uploaded / latest / most recent'. Runs with keyring auth."""
import json, subprocess, os, uuid, sys

PROFILE = "YOUR_PROFILE"
SID = "YOUR_GENIE_SPACE_ID"
NEW_TABLE = "acme_sports.demo.uploaded_docs"
NEW_INSTRUCTION = (
    "LIVE UPLOADED DOCUMENTS (uploaded_docs table):\n"
    "- uploaded_docs holds documents uploaded through the Acme Sports app — parsed the instant "
    "they are uploaded. Columns: doc_type ('contract' or 'voice_note'), player_name, club, "
    "uploaded_at (timestamp), source_file, summary, details (JSON: for contracts end_date/annual_wage/"
    "release_clause/flags; for voice_notes scout/player_id).\n"
    "- This table is the SOURCE OF TRUTH for anything the user 'just uploaded' or asks for the "
    "'latest' / 'most recent' / 'recently uploaded' contract or voice note / voice memo. It is always "
    "current — ALWAYS prefer uploaded_docs over the documents volume for freshly uploaded documents, "
    "and never claim a document doesn't exist without checking uploaded_docs first.\n"
    "- 'What does <player>'s contract say' or 'the contract I just uploaded': "
    "SELECT summary, details FROM uploaded_docs WHERE doc_type='contract' AND player_name ILIKE '%<name>%' "
    "ORDER BY uploaded_at DESC LIMIT 1.\n"
    "- 'Latest voice note / most recent scout memo': "
    "SELECT player_name, summary, uploaded_at FROM uploaded_docs WHERE doc_type='voice_note' "
    "ORDER BY uploaded_at DESC LIMIT 1.")
NEW_QUESTIONS = [
    "What does the contract I just uploaded say?",
    "Summarize the most recent voice note uploaded in the app",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)  # keyring auth (no plaintext env)


def main():
    r = run(["databricks", "genie", "get-space", SID, "--include-serialized-space",
             "-p", PROFILE, "-o", "json"])
    if r.returncode != 0:
        print("GET failed:", r.stderr); sys.exit(1)
    full = json.loads(r.stdout)
    s = full["serialized_space"]
    s = json.loads(s) if isinstance(s, str) else s

    tables = s.setdefault("data_sources", {}).setdefault("tables", [])
    have = {t.get("identifier") for t in tables}
    if NEW_TABLE not in have:
        tables.append({"identifier": NEW_TABLE})
    tables.sort(key=lambda t: t.get("identifier", ""))
    s["data_sources"]["tables"] = tables

    ti = s.setdefault("instructions", {}).setdefault("text_instructions", [])
    if not ti:
        ti.append({"id": uuid.uuid4().hex, "content": []})
    it0 = ti[0]
    content = it0.get("content")
    content = [content] if isinstance(content, str) else (content or [])
    joined = "\n".join(content)
    if "LIVE UPLOADED DOCUMENTS" not in joined:
        content = [joined + "\n\n" + NEW_INSTRUCTION] if joined else [NEW_INSTRUCTION]
    it0["content"] = content
    ti[:] = [it0]

    sq = s.setdefault("config", {}).setdefault("sample_questions", [])
    existing_q = {q for item in sq for q in (item.get("question") or [])}
    for q in NEW_QUESTIONS:
        if q not in existing_q:
            sq.append({"id": uuid.uuid4().hex, "question": [q]})

    ti.sort(key=lambda x: x.get("id", ""))
    sq.sort(key=lambda x: x.get("id", ""))
    print("tables now:", [t["identifier"] for t in tables])

    upd = run(["databricks", "genie", "update-space", SID,
               "--serialized-space", json.dumps(s), "-p", PROFILE, "-o", "json"])
    if upd.returncode != 0:
        print("UPDATE failed:\n", upd.stderr, upd.stdout); sys.exit(1)
    print("UPDATE ok")


if __name__ == "__main__":
    main()

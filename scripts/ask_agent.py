#!/usr/bin/env python3
"""Ask the Acme Scout Genie Agent a question in AGENT MODE (required for file/volume
retrieval) and print the final cited report. Parses the SSE stream.

Usage: python3 ask_agent.py "your question"
Returns final assistant markdown + a list of citation URLs (table vs volume).
"""
import json, subprocess, os, sys, urllib.request

PROFILE = "fe-vm-classic-stable-9cgeia"
HOST = "https://fevm-classic-stable-9cgeia.cloud.databricks.com"
AGENT_ID = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".space_id")).read().strip()
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}


def token():
    r = subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
                       capture_output=True, text=True, env=ENV)
    return json.loads(r.stdout)["access_token"]


def ask(question, timeout=300):
    body = json.dumps({"input": [{"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": question}]}]}).encode()
    req = urllib.request.Request(f"{HOST}/api/2.0/genie/agents/{AGENT_ID}/responses",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    final, convo = None, None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            evt = json.loads(line[5:])
            if evt.get("type") == "response.completed":
                r = evt["response"]
                convo = r.get("conversation_id")
                for item in r.get("output", []):
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        final = "".join(c.get("text", "") for c in item.get("content", []))
            if evt.get("type") == "response.failed":
                return {"error": evt["response"].get("error"), "conversation_id": evt["response"].get("conversation_id")}
    # classify citations
    cites = {"table": [], "volume": []}
    import re
    for url in re.findall(r"\((https?://[^)]+)\)", final or ""):
        (cites["volume"] if "/explore/data/volumes/" in url else cites["table"]).append(url)
    return {"answer": final, "conversation_id": convo, "citations": cites}


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "What is Cristian Mosquera's estimated valuation, and what did our scout say about him?"
    out = ask(q)
    if out.get("error"):
        print("FAILED:", out["error"]); sys.exit(1)
    print(out["answer"])
    print("\n--- citations ---")
    print("table  :", len(out["citations"]["table"]), out["citations"]["table"][:1])
    print("volume :", len(out["citations"]["volume"]), out["citations"]["volume"][:1])

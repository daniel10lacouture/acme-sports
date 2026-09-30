#!/usr/bin/env python3
"""FM vision QA over the FINAL headshot crops: confirm single-person head-and-shoulders
portrait + describe kit (identity is human-verified separately; the model must not name)."""
import os, json, base64, subprocess, urllib.request
PROFILE="fe-vm-classic-stable-9cgeia"; HOST="https://fevm-classic-stable-9cgeia.cloud.databricks.com"
ENV={**os.environ,"DATABRICKS_AUTH_STORAGE":"plaintext"}; VP="databricks-gpt-5-mini"
D="app/static/headshots"
PROMPT=("You are QAing a headshot avatar. Reply ONLY compact JSON: "
 '{"single_person":true/false,"head_and_shoulders":true/false,"face_visible":true/false,'
 '"kit_or_clothing":"short desc"}. head_and_shoulders=true if the head is clearly the main subject '
 "(portrait/upper-body), false if it is a wide/full-body/crowd shot. Do not name the person.")
tok=json.loads(subprocess.run(["databricks","auth","token","-p",PROFILE],capture_output=True,text=True,env=ENV).stdout)["access_token"]
out={}
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".jpg"): continue
    b64=base64.b64encode(open(os.path.join(D,fn),"rb").read()).decode()
    body={"messages":[{"role":"user","content":[{"type":"text","text":PROMPT},
        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],"max_tokens":150}
    req=urllib.request.Request(f"{HOST}/serving-endpoints/{VP}/invocations",data=json.dumps(body).encode(),
        method="POST",headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"})
    txt=json.load(urllib.request.urlopen(req,timeout=120))["choices"][0]["message"]["content"].strip()
    txt=txt.replace("```json","").replace("```","").strip()
    try: j=json.loads(txt)
    except: j={"raw":txt[:120]}
    out[fn]=j
    print(f"{fn:16} {j}")
json.dump(out,open(f"{D}/_qa.json","w"),indent=1)
ok=sum(1 for j in out.values() if j.get("head_and_shoulders") and j.get("single_person"))
print(f"\nFM QA: {ok}/{len(out)} pass single-person head-and-shoulders")

# Databricks notebook source
# MAGIC %md
# MAGIC # ⚽ Acme Sports — Live Demo Runbook
# MAGIC
# MAGIC A conversational **scout-reporting agent** for Acme Sports (football squad-planning SaaS)
# MAGIC that reasons over **structured squad data + unstructured documents** (contract PDFs +
# MAGIC scout-note transcripts), demoable from the **Genie One iOS app**, plus a custom
# MAGIC **Databricks App** that mirrors the Acme Sports product with two working upload flows
# MAGIC and semantic **Scouting Clip Search**.
# MAGIC
# MAGIC > **How to use this notebook:** present top-to-bottom. Grey markdown cells are your
# MAGIC > talk-track; run the code cells to show the real thing. A 5–7 min run-of-show is at the end.
# MAGIC
# MAGIC ### Architecture at a glance
# MAGIC | Layer | What | Where |
# MAGIC |---|---|---|
# MAGIC | Structured | `players`, `contracts`, `scouting_targets`, `scout_reports` | `acme_sports.demo` |
# MAGIC | Unstructured | contract PDFs + scout transcripts | Volume `acme_sports.demo.documents` |
# MAGIC | Images | player clips (extensible to video frames) | Volume `acme_sports.demo.clips` |
# MAGIC | Reasoning | **Acme Scout** Genie Agent (tables + documents volume) | Genie · Agent mode |
# MAGIC | Experience | Genie One mobile + custom **Databricks App** | see URLs below |
# MAGIC | Compute | serverless **Genie-Warehouse** | `84c07276d33bc0a0` |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0 · Resources (the concrete handles)
# MAGIC - **Catalog / schema:** `acme_sports.demo`
# MAGIC - **Warehouse:** Genie-Warehouse (`84c07276d33bc0a0`)
# MAGIC - **Genie Agent "Acme Scout":** `space_id 01f19b59e604108aba34eda9d7e97569`
# MAGIC   → https://fevm-classic-stable-9cgeia.cloud.databricks.com/genie/rooms/01f19b59e604108aba34eda9d7e97569
# MAGIC - **App:** https://acme-sports-7474652196525510.aws.databricksapps.com
# MAGIC - **Volumes:** `/Volumes/acme_sports/demo/documents` (contracts, transcripts, audio) · `/Volumes/acme_sports/demo/clips`

# COMMAND ----------

CATALOG, SCHEMA = "acme_sports", "demo"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
print("Using", CATALOG, SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · The data — one squad, fully modelled
# MAGIC Talk track: *"Everything a sporting director needs — ratings, valuations, contracts, and
# MAGIC a scouting shortlist — in Unity Catalog. 20 players: first team, academy, and targets."*

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT tier, count(*) AS players, round(avg(gpr),1) AS avg_gpr,
# MAGIC        round(sum(wage_per_yr),1) AS wage_bill_eur_m
# MAGIC FROM players GROUP BY tier ORDER BY players DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Top squad members by Acme Player Rating (GPR)
# MAGIC SELECT name, club, positions, gpr, est_valuation_high AS val_high_eur_m,
# MAGIC        wage_per_yr AS wage_eur_m, months_left, status
# MAGIC FROM players ORDER BY gpr DESC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Scouting shortlists + the release clause we parsed from each target's contract PDF
# MAGIC SELECT s.list_name, p.name, s.club, s.positions, s.gpr, c.release_clause AS clause_eur_m
# MAGIC FROM scouting_targets s
# MAGIC JOIN players p USING(player_id)
# MAGIC LEFT JOIN contracts c USING(player_id)
# MAGIC ORDER BY s.list_name, s.gpr DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Unstructured ingestion — documents become queryable
# MAGIC Talk track: *"Scouting lives in PDFs and voice notes. We keep them in a UC Volume and
# MAGIC parse at query time — no separate index to keep in sync, so new intel is instantly usable."*

# COMMAND ----------

# List the documents volume (contract PDFs + scout transcripts + uploaded audio)
for sub in ["contracts", "transcripts", "audio"]:
    try:
        files = dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/documents/{sub}")
        print(f"\n{sub}/  ({len(files)} files)")
        for f in files[:6]:
            print("  ", f.name)
    except Exception as e:
        print(sub, "->", e)

# COMMAND ----------

# MAGIC %md
# MAGIC **The `ai_extract` beat:** contract end dates + release clauses in the `contracts` table
# MAGIC were **not typed in by hand** — they were extracted from the PDFs with
# MAGIC `ai_parse_document` + `ai_extract`. Show it live on one contract:

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ai_extract(
# MAGIC          CAST(ai_parse_document(content) AS STRING),
# MAGIC          array('contract_start_date','contract_end_date','release_clause_in_euros')
# MAGIC        ) AS extracted
# MAGIC FROM READ_FILES('/Volumes/acme_sports/demo/documents/contracts/contract_saka.pdf',
# MAGIC                  format => 'binaryFile');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- The structured result of that extraction, ready for SQL filtering (hybrid: numbers here, clause text in the docs)
# MAGIC SELECT p.name, c.contract_end, c.release_clause AS clause_eur_m, c.transfer_status
# MAGIC FROM contracts c JOIN players p USING(player_id)
# MAGIC WHERE c.release_clause IS NOT NULL
# MAGIC ORDER BY c.release_clause DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · 🌟 The hero moment — Acme Scout blends structured + unstructured
# MAGIC Talk track: *"Now watch one question pull a number from a table AND an opinion from a
# MAGIC scout's voice note — with citations to both."*
# MAGIC
# MAGIC ### Demo it on **Genie One (mobile)** — the money shot
# MAGIC 1. Open **Genie One** on the phone → open the **Acme Scout** agent.
# MAGIC 2. **Turn ON Agent mode** in the chat box *(required — file/volume retrieval only runs in Agent mode)*.
# MAGIC 3. Ask these (copy/paste ready):
# MAGIC    - **Blended:** *"What is Cristian Mosquera's estimated valuation, and what did our scout say about him?"*
# MAGIC    - **Doc-only:** *"According to his contract, what is Vitor Roque's release clause and end date?"*
# MAGIC    - **Structured:** *"Which first-team players have under 24 months left on their contract?"*
# MAGIC    - **Decision:** *"Which centre-back is the best value, and do the scouts or contracts raise concerns?"*
# MAGIC
# MAGIC Expect a narrative answer with **[1]/[2] citations** — one to a SQL query, one to a document in the volume.

# COMMAND ----------

# MAGIC %md
# MAGIC **Optional — prove it from code** (same Agent-mode API the app uses). Run to show the blended, cited answer inline.

# COMMAND ----------

import json, urllib.request
AGENT_ID = "01f19b59e604108aba34eda9d7e97569"
HOST = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
# In a notebook, use the notebook's auth token:
TOK = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

def ask_acme_scout(question, timeout=300):
    body = json.dumps({"input": [{"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": question}]}]}).encode()
    req = urllib.request.Request(f"{HOST}/api/2.0/genie/agents/{AGENT_ID}/responses",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    answer = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            evt = json.loads(line[5:])
            if evt.get("type") == "response.completed":
                for it in evt["response"].get("output", []):
                    if it.get("type") == "message" and it.get("role") == "assistant":
                        answer = "".join(c.get("text", "") for c in it.get("content", []))
    return answer

print(ask_acme_scout("What is Cristian Mosquera's estimated valuation, and what did our scout say about him?"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · The app — looks/feels like the real Acme Sports product
# MAGIC **URL:** https://acme-sports-7474652196525510.aws.databricksapps.com  *(open in a browser signed into this workspace)*
# MAGIC
# MAGIC Walk the left nav (light product theme):
# MAGIC - **Home** — greeting, Ask bar with suggested chips, "Pinned for you" (Squad + Scouting summaries), activity feed, GPR donut.
# MAGIC - **Scouting** — *Watchlists* (filterable target table), *Boards*/*Shadow Team* [SOON], and **Scout Reports** (voice note upload).
# MAGIC - **Squad [BETA]** — KPIs (wage bill, players, capital gains, acquisition cost); *Planning* (4-3-3 formation pitch + First Team & Academy tables), **Contracts** (contract table + PDF upload), *Financials*/*Analysis* [SOON]. Click any player for the rich profile card.
# MAGIC - **Ask Acme AI** — a styled placeholder (the deep reasoning lives in Acme One mobile, see §3).
# MAGIC - **Clip Search** — §5.
# MAGIC
# MAGIC ### Two LIVE upload flows
# MAGIC 1. **Contract PDF** — *Squad → Contracts → Upload a contract PDF* → writes to `documents/contracts/` via the UC Volumes Files API; `ai_extract` reads the end date & clause.
# MAGIC 2. **Voice scout note** — *Scouting → Scout Reports → Record note* → browser transcribes speech live → audio + transcript land in `documents/transcripts/`.
# MAGIC    *(Production path documented: swap in a Whisper Model Serving endpoint via `TRANSCRIBE_ENDPOINT`.)*
# MAGIC
# MAGIC ### 🎣 The killer beat: "upload, then ask on the phone — it already knows"
# MAGIC Upload a new contract or record a note in the app, then immediately ask Acme Scout about that
# MAGIC player on your phone (Agent mode on). Because we parse the volume at query time, **the answer
# MAGIC reflects the brand-new document with no reindex step.**

# COMMAND ----------

# Show what's currently in the volume so you can prove "it just appeared" after a live upload
print("contracts/:", [f.name for f in dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/documents/contracts")])
print("transcripts/:", [f.name for f in dbutils.fs.ls(f"/Volumes/{CATALOG}/{SCHEMA}/documents/transcripts")])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Scouting Clip Search — semantic image search (extensible to video)
# MAGIC Talk track: *"Type a player and get their clips. Under the hood: a Foundation-Model vision
# MAGIC model captions every image, we embed the captions, and match your query by similarity.
# MAGIC The exact same pipeline runs per **video frame** — this is the storytelling hook."*
# MAGIC
# MAGIC In the app → **Clip Search**, type:
# MAGIC - **`Luis Diaz`** → resolves to **one player**, shows only Luis Díaz's gallery (4 clips).
# MAGIC - **`Rodri`** → only Rodri's clips.
# MAGIC - **`player in a red kit`** (secondary "scene" mode) → ranked clips across players — real image understanding, not filename matching.

# COMMAND ----------

# The index behind Clip Search: one row per image, with an FM vision caption + embedding
display(spark.sql(f"""
  SELECT player_id, name, club, count(*) AS clips
  FROM {CATALOG}.{SCHEMA}.clip_index
  GROUP BY player_id, name, club ORDER BY clips DESC, name"""))

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Peek at the FM-generated vision captions (this is the "image understanding" that powers search)
# MAGIC SELECT name, caption FROM clip_index WHERE player_id IN ('ext_ldiaz','ext_rodri') ORDER BY name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · ▶️ Suggested run-of-show (5–7 minutes)
# MAGIC | Time | Beat | Do / Say |
# MAGIC |---|---|---|
# MAGIC | 0:00 | **Frame it** | "Acme Sports plans squads. Their intel is split across tables AND documents. Here's one assistant over both." |
# MAGIC | 0:45 | **Data** (§1) | Run the tier + top-GPR queries. "20 players, fully modelled in Unity Catalog." |
# MAGIC | 1:30 | **Documents + ai_extract** (§2) | List the volume, run the `ai_extract` cell. "Release clauses were read out of the PDFs — no manual entry." |
# MAGIC | 2:45 | **🌟 Genie One on phone** (§3) | Agent mode ON, ask the blended Mosquera question. "One answer, two sources, cited." |
# MAGIC | 4:00 | **The app** (§4) | Tour the UI; upload a contract PDF live. |
# MAGIC | 4:45 | **Upload→ask beat** | Ask about that player on the phone — "it already knows," no reindex. |
# MAGIC | 5:30 | **Clip Search** (§5) | Type "Luis Diaz" then "Rodri" → single-player galleries. "Same pipeline runs on video frames." |
# MAGIC | 6:30 | **Close** | Name-drop the platform (below) and hand back. |
# MAGIC
# MAGIC ### Databricks capabilities to name-drop
# MAGIC - **Genie Agents over Unity Catalog Volumes** (Beta) — blended structured + unstructured, with citations, in **Agent mode**; reachable from **Genie One** mobile.
# MAGIC - **`ai_parse_document` + `ai_extract`** — documents → structured columns, in plain SQL.
# MAGIC - **Foundation Model APIs for image understanding** — vision captioning + text embeddings power Clip Search (and video frames).
# MAGIC - **Databricks Apps** — a branded product-grade UI (React-style SPA + FastAPI) with live UC Volume writes, deployed on the platform.
# MAGIC - **Unity Catalog** governs it all — one permission model across tables, volumes, the agent, and the app's service principal.
# MAGIC
# MAGIC *Fin. Break a leg. ⚽*

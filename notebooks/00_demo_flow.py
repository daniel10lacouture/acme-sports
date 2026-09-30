# Databricks notebook source
# MAGIC %md
# MAGIC # 🎬 Acme Sports — Demo Flow & Tee-Up
# MAGIC ### How to run the demo, in order, with the hook + the "art of the possible" line for each beat
# MAGIC
# MAGIC This is the **run-of-show**. `99_demo_runbook.py` is the deep architecture walkthrough;
# MAGIC this notebook is what you keep open on the second screen while you present.
# MAGIC
# MAGIC **App:** https://acme-sports-WORKSPACE_ID.aws.databricksapps.com
# MAGIC **Genie (Acme Scout):** space `YOUR_GENIE_SPACE_ID` · Agent mode
# MAGIC **Catalog/Schema/Volume:** `acme_sports.demo` · Volume `documents` · Warehouse `Genie-Warehouse`
# MAGIC
# MAGIC > **The persona:** you are the **Sporting Director** of Arsenal. Everything is framed as *my* decisions
# MAGIC > about *my* squad — recruitment, contracts, valuations, fitness, and scouting film. Stay in character.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 The problem statement (open with this — 45 seconds)
# MAGIC
# MAGIC > *"A modern football club's most valuable intelligence is trapped in **four different formats that don't talk to each other**:
# MAGIC > structured data (ratings, wages, minutes) lives in the analytics team's warehouse; **contracts are PDFs** in a legal
# MAGIC > folder; **scout observations are voice notes and text** on someone's phone; and **the actual football — the film —**
# MAGIC > sits in a video archive nobody can search. So the Sporting Director can't ask one simple question and get one answer.*
# MAGIC >
# MAGIC > *Today I'll show you a single governed platform on Databricks where all four live together, one AI assistant answers
# MAGIC > across all of them **with citations**, and I can search my video archive by **name or by what's happening on the pitch.**
# MAGIC > No data left the platform. No model was trained on someone else's data. It's all governed by Unity Catalog."*
# MAGIC
# MAGIC **Why it lands:** every exec has the "our data is in silos and our AI can't be trusted" problem. This reframes it as *governed, cited, multimodal, one place.*

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🗺️ Run-of-show (5–7 min) — the order to click
# MAGIC
# MAGIC | # | Beat | Where | The one-liner hook |
# MAGIC |---|------|-------|--------------------|
# MAGIC | 1 | **Home / squad at a glance** | App ▸ Home | *"Everything I know about my squad, live from the lakehouse."* |
# MAGIC | 2 | **Upload a contract PDF** | App ▸ Squad ▸ Contracts | *"Watch unstructured data become governed data in one drop."* |
# MAGIC | 3 | **Record a voice scout note** | App ▸ Scouting ▸ Scout Reports | *"My scout talks; the platform transcribes and files it — instantly searchable."* |
# MAGIC | 4 | **Ask Acme Scout (the hero)** | Genie One / App ▸ Ask | *"One question. Answer from the numbers AND the contract PDF — with a citation."* |
# MAGIC | 5 | **Scouting Clip Search** | App ▸ Clip Search | *"Search my film by name — or by what's happening on the pitch."* |
# MAGIC | 6 | **What-If planning (bonus)** | App ▸ Squad ▸ Planning | *"Model a transfer window and see squad value move — persisted transactionally."* |
# MAGIC | 7 | **AI Transfer Assistant** | App ▸ Acme Agents ▸ AI Transfer | *"Drag the KPIs that drive value — position-aware, live, and explainable to the last euro."* |
# MAGIC | 8 | **AI Physio / Load Manager** | App ▸ Acme Agents ▸ AI Physio | *"Who's spiking, and how many minutes on Saturday — from WHOOP + GPS, with an AI rationale."* |
# MAGIC | 9 | **AI Nutrition Assistant** | App ▸ Acme Agents ▸ AI Nutrition | *"A fuelling plan that knows the player's load — and adapts to a voice note."* |
# MAGIC | 10 | **AI Coach Assistant** | App ▸ Acme Agents ▸ AI Coach Assistant | *"A full match-prep brief on the next opponent — with the scouting clips cited."* |
# MAGIC | 11 | **AI Financial Analyst** (was FFP & Contracts) | App ▸ Acme Agents ▸ AI Financial Analyst | *"How much can I actually spend? Squad-cost ratio, PSR headroom, and the contract receipts."* |
# MAGIC
# MAGIC Close on the Genie hero moment or the Clip Search — both are the "wow." Beat 6 is your "and there's more" if the room is technical/leans in.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 1 ──  Contract PDF upload → governed UC Volume
# MAGIC
# MAGIC **What you do:** In the app, go **Squad ▸ Contracts**, drag in a contract PDF. It lands in
# MAGIC `/Volumes/acme_sports/demo/documents/contracts/` via the Files API. Show it appear in the list.
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - The file is written to a **Unity Catalog Volume** — the same governance boundary as tables (grants, lineage, audit).
# MAGIC - `ai_parse_document` + `ai_extract` then read the PDF and pull **structured fields** (release clause €M, contract end date)
# MAGIC   into the `contracts` Delta table. *Proven: Saka's €180M clause and 2027-06-30 end date came out of the PDF, not a spreadsheet.*
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"That PDF didn't go to some SaaS inbox — it landed **inside my catalog**, governed like any table. And I don't have to
# MAGIC > read 40 pages: Databricks parsed the release clause and the expiry straight into a column I can filter on. Every contract
# MAGIC > in the club becomes a queryable row **and** stays a citable document."*
# MAGIC
# MAGIC **Capabilities to name-drop:** Unity Catalog Volumes · Files API · `ai_parse_document` · `ai_extract` · Delta.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 2 ──  Voice scout note → transcript in the Volume
# MAGIC
# MAGIC **What you do:** **Scouting ▸ Scout Reports**, hit record, speak a short scouting observation
# MAGIC ("Mosquera reads the game well, comfortable stepping into midfield, needs to sharpen his weak foot…"), stop.
# MAGIC The app transcribes it and files both the **audio** and the **transcript**.
# MAGIC
# MAGIC **The technical truth (important — be precise here):**
# MAGIC - The audio (`audio/*.wav`) **and** the transcript (`transcripts/scout_note_*.txt`) both land in the **UC Volume** —
# MAGIC   **not** a Delta table. That transcript file is what Acme Scout later reads and cites.
# MAGIC - Transcription today runs via the **browser Web Speech API** (works with zero infra). It's a **one-env-var swap**
# MAGIC   (`TRANSCRIBE_ENDPOINT`) to move to a **Whisper Model Serving** endpoint server-side — no app code change. Say that:
# MAGIC   it shows the production path without pretending we deployed a GPU we didn't.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"My scout is pitchside in Portugal — he doesn't type a report, he **talks**. Seconds later that observation is a governed
# MAGIC > text file sitting next to the contract and the ratings, and my AI assistant can quote it back to me. Unstructured, multimodal
# MAGIC > capture, zero friction for the person in the field."*
# MAGIC
# MAGIC **Capabilities to name-drop:** UC Volumes · multimodal ingestion · Model Serving (Whisper, production path) · governed unstructured storage.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 3 ──  Acme Scout — the AI knowledge assistant (THE HERO MOMENT)
# MAGIC
# MAGIC **What it points to** (Genie Space "Acme Scout", **Agent mode**):
# MAGIC - **8 Delta tables:** `players`, `contracts`, `scouting_targets`, `scout_reports`,
# MAGIC   `player_valuation`, `injury_risk`, `scenario_impact`, `scenario_moves`
# MAGIC - **+ the `documents` UC Volume:** the contract **PDFs** and the scout-note **transcripts** (incl. the voice note from Feature 2)
# MAGIC
# MAGIC **What kinds of questions it answers:**
# MAGIC 1. **Pure structured** — *"Which first-team players have under 18 months left on their contract?"* → SQL over tables.
# MAGIC 2. **Pure document** — *"What is Saka's release clause and when does his deal expire?"* → reads the **PDF** and answers.
# MAGIC 3. **⭐ Blended + cited (the money question)** — *"What's Mosquera worth and what does our scout say about him?"*
# MAGIC    → valuation from the **table** + observation quoted from the **transcript in the volume**, each with a **citation**.
# MAGIC 4. **Fused AI-model** — *"In Scenario B, what's our squad value and who's the highest injury risk?"* → joins scenario + injury tables.
# MAGIC
# MAGIC **Yes — it cites the PDF.** This is exactly the "knowledge-assistant" behaviour you were asking about: Agent mode does
# MAGIC **retrieval over the volume**, pulls the relevant contract/transcript, and returns the answer **with a citation to the source file**.
# MAGIC (Verified end-to-end: Saka €180M + 30-Jun-2027 came back cited to the PDF; blended answers cite BOTH a SQL result AND a volume file.)
# MAGIC
# MAGIC > ⚠️ **Demo mechanics:** file/volume retrieval works **only in Agent mode** (`/genie/agents/{id}/responses`, or the Agent-mode
# MAGIC > toggle in the Genie One chat box). Plain chat mode won't read the volume. Turn Agent mode ON before you ask the document question.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"This is the part that usually makes people nervous about AI — 'can I trust the answer?' Watch: I ask one question in plain
# MAGIC > English, and it answers from my **live numbers and the actual signed contract**, and it **shows me its sources**. It's not
# MAGIC > guessing — it's reading my governed data and citing it. That's the difference between a chatbot and a knowledge assistant."*
# MAGIC
# MAGIC **Capabilities to name-drop:** Genie / AI-BI · Genie Agent mode (retrieval + citations over Volumes) · natural-language-to-SQL · governed, grounded, cited answers.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Copy-paste questions for the Genie hero moment (in escalation order)
# MAGIC
# MAGIC 1. `Which first-team players have fewer than 18 months left on their contract?`  *(structured)*
# MAGIC 2. `What is Bukayo Saka's release clause and when does his contract end?`  *(reads the PDF)*
# MAGIC 3. `What is our valuation of Cristian Mosquera and what does the latest scout report say about him?`  *(BLENDED + cited — the wow)*
# MAGIC 4. `In Scenario B, what's our projected squad value and who is our highest injury risk?`  *(fused AI models)*
# MAGIC
# MAGIC Pause on #3 and physically point at the citation. That's the moment.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 4 ──  Scouting Clip Search — search the film
# MAGIC
# MAGIC **What you do:** **Clip Search**. Type a **name** (`Vini Jr`, `Luis Diaz`), then type a **description** (`player in a red kit`).
# MAGIC Video cards play inline.
# MAGIC
# MAGIC **The two paths — say this out loud, it's the clever bit:**
# MAGIC - **Name query → deterministic resolver.** `vini jr` / `luis diaz` resolve **exactly** to that one player and return **only**
# MAGIC   that player's clips — **zero other players, no embedding fuzziness.** (This is the accuracy fix: a name is a filter, not a vibe.)
# MAGIC - **Descriptive query → semantic search.** `player in a red kit`, `goalkeeper`, `celebration` have no name to match, so it falls
# MAGIC   back to **embedding similarity over the clips** — real "search by what's happening."
# MAGIC
# MAGIC **How the film is actually indexed (honest pipeline):** each video is frame-sampled with ffmpeg → each frame **captioned by a
# MAGIC vision model** (`databricks-gpt-5-mini`) → caption **embedded** (`databricks-gte-large-en`, 1024-dim) → one governed row in
# MAGIC `clip_index` with `player_name`, `video_url`, `poster_path` as first-class columns. So "semantic search over video" is literally true.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"My video archive used to be a folder nobody opened. Now I search it two ways: by **name**, and it's dead-accurate — only that
# MAGIC > player, every time; or by **what I'm looking for on the pitch** — 'a player in a red kit', 'a goalkeeper' — and it understands
# MAGIC > the football in the frame. Same platform, same governance, now including the film."*
# MAGIC
# MAGIC **Capabilities to name-drop:** Foundation Model APIs (vision captioning) · embedding endpoints · vector similarity · UC Volumes for video · governed multimodal retrieval.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 5 (bonus) ──  What-If planning + valuation + injury risk (Lakebase)
# MAGIC
# MAGIC **What you do:** **Squad ▸ Planning** — flip between **Current / Scenario A / B**, watch the header (squad value, wage bill,
# MAGIC capital gains) recompute; open a **player card** to show the **What-If Valuation waterfall**.
# MAGIC
# MAGIC **The technical truth:**
# MAGIC - Scenarios are written **transactionally to Lakebase (Postgres/OLTP)** and read straight back — real operational writes from an app.
# MAGIC - Valuation is a **Model Serving** endpoint (`acme-valuation`) with **explainability**: the waterfall shows a peer baseline,
# MAGIC   then each factor (rating, age, contract, minutes) moving value up/down, ending at the final €M — and it **ties to the header**.
# MAGIC - **Injury & load-risk** is a second model scored into Delta, surfaced as availability, and answerable in Genie.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"I can model a transfer window — sell here, promote there, sign a target — and see my squad value and wage bill move in real
# MAGIC > time, saved transactionally so my analysts see the same scenario I do. And every valuation is **explainable** — I can show the
# MAGIC > board exactly why we value a player at €115M, factor by factor. Operational app, analytical models, one platform."*
# MAGIC
# MAGIC **Capabilities to name-drop:** Lakebase (managed Postgres) · synced tables · Model Serving + MLflow · explainable ML · transactional app writes on the lakehouse.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 6 ──  AI Transfer Assistant — interactive, explainable valuation
# MAGIC
# MAGIC **What you do:** **Acme Agents ▸ AI Transfer** tab. Pick a player — the sliders **change with the position**
# MAGIC (a striker shows goals/xG/shot conversion/pressures; a centre-back shows tackles+interceptions/
# MAGIC aerial-duel%/progressive passes; a keeper shows clean-sheet%/save%/aerial claims). **Drag a slider**
# MAGIC and the value on the right **recomputes live**, with a factor-by-factor breakdown of *why*.
# MAGIC Also reachable from any **player card** (the "AI Transfer Valuation" block → *Open the interactive valuation*).
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - The value is a **calibrated, position-specific model** served on **Model Serving**
# MAGIC   (`acme-transfer-valuation`, serverless scale-to-zero) — a transparent additive pyfunc
# MAGIC   (`value = peer base + Σ per-driver contribution`), so every euro is **explainable**, not a black box.
# MAGIC - KPIs are **synthetic, Opta/StatsBomb-shaped** (`player_kpis` table) — the live stats feed is a
# MAGIC   **one-config swap**. The model is **illustrative / tied to plausible market ranges**; the **production
# MAGIC   path** is **AutoML / regression trained on historical transfer fees** — same app, swap the coefficients.
# MAGIC - The UI recomputes locally for instant slider feedback and hits the endpoint on load / "Recompute on
# MAGIC   Model Serving" — the served model and the local math agree (verified in `check_run.py`).
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"Valuation isn't one number — it's a conversation. I can sit with my board, drag 'goals per 90' up,
# MAGIC > and watch €18M appear on the price **with the reason attached**. It's position-aware — a keeper and a
# MAGIC > striker are valued on completely different things — and it's explainable to the last euro. That's a model
# MAGIC > I can defend in a negotiation, not a spreadsheet I have to trust."*
# MAGIC
# MAGIC **Copy-paste demo beats:** open **Saka** (≈€146M, goals/xG/conversion dominate) → drag **Goals /90** down,
# MAGIC watch value fall → switch to **Raya (GK)** to show the drivers change entirely → open a **player card** and
# MAGIC click into the assistant.
# MAGIC
# MAGIC **Capabilities to name-drop:** Model Serving (serverless) · MLflow pyfunc · explainable/additive ML ·
# MAGIC transparent calibrated model with an AutoML production path · one-config live-data swap.
# MAGIC
# MAGIC > This **replaces** the old static what-if waterfall in the player card with a live, interactive, position-aware tool.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 7 ──  AI Physio / Load Manager — minutes management from wearables
# MAGIC
# MAGIC **What you do:** **Acme Agents ▸ AI Physio** tab. The **squad load board** ranks players most-at-risk first
# MAGIC (Red/Amber/Green) with ACWR, 7-day minutes, WHOOP recovery, sleep, injury band and a **recommended
# MAGIC minutes for the next fixture**. Click a player → GPS-load and recovery **trend sparklines**, then hit
# MAGIC **Generate recommendation** for a live, grounded rationale.
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - Two provider-shaped feeds: **WHOOP** (recovery / sleep / HRV → `whoop_daily`) and **STATSports** GPS
# MAGIC   (distance / high-speed / player-load → `statsports_sessions`) fuse into a **`load_status`** snapshot with
# MAGIC   **ACWR** (acute:chronic workload ratio — the sports-science overload signal; >1.3 is the danger zone).
# MAGIC - The next-fixture minutes recommendation comes off that snapshot, and the per-player **rationale is
# MAGIC   generated LIVE by `ai_query`** over the player's own figures — grounded, not scripted.
# MAGIC - Data is **synthetic / representative** today; the **WHOOP/STATSports connector is a one-config swap**
# MAGIC   (`notebooks/ingest_whoop.py`) — same honesty pattern as the rest of the demo.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"My sports scientists live in WHOOP and STATSports; my recruitment team lives in the ratings. Here they're
# MAGIC > the same platform. I can see at a glance who's spiking — ACWR in the red — and get an AI recommendation on
# MAGIC > exactly how many minutes to give a player on Saturday, with the reason. That's how you stop a €100M asset
# MAGIC > from tearing a hamstring because nobody joined the fitness data to the football."*
# MAGIC
# MAGIC **New audience:** this section is for your **performance & medical staff** — sports scientists and physios —
# MAGIC a room that never had a reason to open Acme before. The platform just grew past recruitment into the medical wing.
# MAGIC
# MAGIC **Capabilities to name-drop:** multimodal/operational data fusion on the lakehouse · `ai_query` (FM APIs)
# MAGIC for grounded natural-language rationale · governed synthetic data with a one-config live-connector swap.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 8 ──  AI Nutrition Assistant — tailored fuelling from load + a voice note
# MAGIC
# MAGIC **What you do:** **Acme Agents ▸ AI Nutrition** tab. Pick a player — you see their fuelling-relevant metrics
# MAGIC (distance, sleep, WHOOP recovery, next-match load, estimated daily energy). Optionally **record a
# MAGIC voice note** (same voice pipeline as scout reports) or type dietary context. Hit **Generate fuelling
# MAGIC plan** → a tailored plan: daily kcal / carbs / protein, hydration, pre-match, matchday, recovery, and a
# MAGIC personalised note.
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - It **reuses two things you've already seen**: the **physio load/recovery data** and the **voice pipeline**.
# MAGIC   The plan is generated **live by `ai_query`** (FM), grounded in the player's own numbers **and** the voice
# MAGIC   note — so "prefers rice over pasta, lactose intolerant, big match Sunday" actually changes the output.
# MAGIC - Returned as **structured JSON** and rendered as a plan card (macros + timed guidance), not a wall of text.
# MAGIC - Metrics are synthetic (physio feed) — one-config swap to live WHOOP/STATSports; voice capture is the
# MAGIC   browser Web Speech pipeline (same one-env-var Whisper production path as the scout notes).
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"Same platform, same data — now my nutritionist gets a fuelling plan that already knows this player ran
# MAGIC > 77km last week, slept badly, and has a big match Sunday. My player just **talks** — 'I prefer rice, I'm
# MAGIC > lactose intolerant' — and the plan adapts. That's personalised sports science at squad scale, with zero
# MAGIC > new tooling."*
# MAGIC
# MAGIC **New audience:** this brings in **performance nutrition** — the nutritionist/dietitian — who reviews changes
# MAGIC vs a baseline rather than building plans from scratch. Another department, same governed platform, no new tool.
# MAGIC
# MAGIC **Capabilities to name-drop:** `ai_query` (FM APIs) with structured JSON output · data + voice reuse across
# MAGIC assistants · governed, grounded, personalised recommendations on one platform.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 9 ──  AI Coach Assistant / Match-Prep — scouting report with clip citations
# MAGIC
# MAGIC **What you do:** **Acme Agents ▸ AI Coach Assistant** tab. Pick the next opponent (Man City / Real Madrid / Bayern) →
# MAGIC you see their **event + tracking metrics** (PPDA, xG for/against, possession, high-press, field tilt),
# MAGIC then an **auto-generated match-prep brief**: how they hurt us, how we beat them, set-piece note, and the
# MAGIC **key battle** — each danger man backed by a **scouting-clip citation** pulled straight from the film index.
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - Opponent metrics are **synthetic but provider-shaped** (Opta/StatsBomb event + SkillCorner tracking columns) —
# MAGIC   the live feed is a one-config swap into the same schema.
# MAGIC - The brief is generated **live by `ai_query`** grounded in those metrics (structured JSON → rendered).
# MAGIC - The **clip citations reuse the exact Clip Search resolver** — "Rodri" resolves to Rodri's film, deterministically.
# MAGIC   So the analyst's claim ("Rodri progresses from deep") links to the actual clip. One index, cited two ways.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"This is a whole analyst's afternoon in one click. It reads the opponent's data, tells me how they'll hurt us
# MAGIC > and exactly how we set up to beat them — and when it says 'watch Rodri drop in and progress', it hands me the
# MAGIC > clip. Data and film, one platform, one governed answer, with the receipts."*
# MAGIC
# MAGIC **New audience:** this is the **coaching staff's** section — head coach and opposition analysts — turning the
# MAGIC same governed film + data into match preparation. The platform now reaches the training ground, not just recruitment.
# MAGIC
# MAGIC **Capabilities to name-drop:** `ai_query` (FM APIs) structured generation · governed multimodal reuse (metrics +
# MAGIC film in one place) · the same embedding/vision clip index cited from a second surface · one-config live-feed swap.

# COMMAND ----------

# MAGIC %md
# MAGIC # ── FEATURE 10 ──  AI Financial Analyst — FFP/PSR compliance + contract economics (exec/CFO-focused)
# MAGIC
# MAGIC **What you do:** **Acme Agents ▸ AI Financial Analyst** tab. A board-level compliance dashboard: wage bill,
# MAGIC transfer-fee **amortization**, **UEFA squad-cost ratio** (vs the 70% cap), **PSR 3-year headroom**,
# MAGIC **investment headroom**, an AI **verdict** (Compliant / Watch / At risk), risk flags, the per-player
# MAGIC contract-economics table, and the **governed contract PDFs as evidence**.
# MAGIC
# MAGIC **The technical truth (say it plainly):**
# MAGIC - Wages + contract dates are the **real** demo `contracts`/`players` data; amortization is computed
# MAGIC   transparently (fee ÷ contract length) from `contract_economics`. Revenue/opex + acquisition fees are
# MAGIC   **illustrative** — a one-config swap to the finance ledger; the model is fully transparent, not a black box.
# MAGIC - The exec verdict is generated **live by `ai_query`** grounded in the computed position (structured JSON).
# MAGIC - The **evidence cards pull the `contract_files` FILE-column table** — `ai_parse_document` read each governed
# MAGIC   PDF and `ai_query` summarised it (Saka's €180M clause / 30-Jun-2027 came out of the FILE). Governance to the doc.
# MAGIC
# MAGIC **🎤 Hook / art-of-the-possible:**
# MAGIC > *"This is the conversation with the board. It reads my real contracts, models my squad-cost ratio and PSR
# MAGIC > headroom, tells me how much I can actually spend this window — and every claim traces back to the signed PDF,
# MAGIC > governed in Unity Catalog. It fills the exact 'Financials' gap that used to say 'coming soon'."*
# MAGIC
# MAGIC **New audience:** this opens the **CFO and the finance function** — FFP/PSR, the board conversation — the
# MAGIC highest-value seat in the building, now working off the same governed data as recruitment. That's the platform play.
# MAGIC
# MAGIC **Capabilities to name-drop:** the **FILE column type** (governed docs as rows) · `ai_parse_document` + `ai_query`
# MAGIC · transparent financial modelling on the lakehouse · governed, evidence-linked exec reporting.
# MAGIC
# MAGIC # COMMAND ----------
# MAGIC
# MAGIC %md
# MAGIC ## 🤖 The Acme Agents suite — an AUDIENCE-EXPANSION play (say this to execs)
# MAGIC
# MAGIC > **The framing that lands with the buyer:** Acme's core users today are the **Sporting Director**
# MAGIC > (signings, contracts, valuations) and the **recruitment analysts**. Every net-new agent in this suite
# MAGIC > **opens a new internal audience inside the same club, on the same governed platform** — so the platform's
# MAGIC > footprint (and its value) grows department by department without a new tool or a new data copy.
# MAGIC
# MAGIC | Agent | What it does | Grounded in | **Opens the audience of…** |
# MAGIC |-------|--------------|-------------|----------------------------|
# MAGIC | **AI Transfer** | Interactive, position-specific, explainable valuation (sliders → live value) | `player_kpis` + Model Serving `acme-transfer-valuation` | Sporting director + recruitment analysts *(core — deepens it)* |
# MAGIC | **AI Physio** | Next-fixture minutes + load management, with a physio-team note folded in | WHOOP + STATSports → `load_status` + `ai_query` | **Performance & medical staff** (sports scientists, physios) |
# MAGIC | **AI Nutrition** | Baseline plan + AI adjustments from load + a voice note | `load_status` + voice pipeline + `ai_query` | **Performance nutrition** (nutritionists / dietitians) |
# MAGIC | **AI Coach Assistant** (was Opposition) | Match-prep brief with scouting-clip citations | `opponents` (Opta/StatsBomb-shaped) + clip index + `ai_query` | **Coaching staff** (head coach, opposition analysts) |
# MAGIC | **AI Financial Analyst** (was FFP & Contracts) | FFP/PSR compliance + forward-looking scenarios + contract evidence | `contract_economics` + `contract_files` (FILE) + `ai_query` | **CFO & the finance function** (FFP/PSR, board) |
# MAGIC
# MAGIC **Why it matters commercially:** you walked in selling to recruitment; you walk out with a platform the
# MAGIC **medical room, the coaches, the nutritionist and the CFO** all have a reason to log into. Same Unity Catalog,
# MAGIC same governance, one more department each time — that is how a single use case becomes a club-wide platform.
# MAGIC
# MAGIC **The through-line:** one governed platform, `ai_query`/Model Serving everywhere, synthetic feeds that
# MAGIC swap to live with one config change, and every AI output **explained or cited** — never a black box.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧵 The closing thread (tie it back — 30 seconds)
# MAGIC
# MAGIC > *"Four formats — numbers, contracts, voice, film — one governed platform. One AI assistant that answers across all of them
# MAGIC > **and cites its sources.** Operational writes and explainable models on the same data. Nothing left Unity Catalog. That's not
# MAGIC > four tools stitched together — that's the Data Intelligence Platform doing what a Sporting Director actually needs."*
# MAGIC
# MAGIC ### If asked "is this real or a mock?"
# MAGIC - The **app is live and deployed**; data is **real Delta tables** in `acme_sports.demo`; PDFs and transcripts are **real files
# MAGIC   in a real UC Volume**; the clips are **real match footage** indexed by real FM vision + embedding endpoints.
# MAGIC - Verification harness `check_run.py` proves the whole chain end-to-end: **40/40 PASS**.
# MAGIC - The only "production-path, not-deployed-here" piece is **server-side Whisper transcription** (one env var away) — say so; it builds trust.
# MAGIC
# MAGIC ### Failure-mode safety (don't get caught)
# MAGIC - **Genie document question returns nothing?** You're not in **Agent mode** — toggle it on.
# MAGIC - **Clip name search looks wrong?** It won't — but if a card looks off, it's still that player's own tagged clip (we curated to content-verified footage).
# MAGIC - **App cold?** First call after idle can lag (scale-to-zero on the valuation endpoint) — click Home once to warm it before you present.

# Acme Sports — On-Site Run of Show

**~35 min (target 30–40) · Sporting-Director demo**
Talk-track condensed from `notebooks/00_demo_flow.py`. Verification: `check_run.py` = **53/53 PASS**. Tag `demo-prep-v1`.

---

## 🃏 One-page cheat card

- **Persona:** you are the **Sporting Director of Arsenal**. Every click is *my* squad, *my* money, *my* film.
- **App:** `https://acme-sports-7474652196525510.aws.databricksapps.com`
- **Genie One (mobile):** space "Acme Scout" · **Agent mode ON**
- **Catalog:** `acme_sports.demo` · Volume `documents` · Warehouse `Genie-Warehouse`
- **Drag-drop asset:** `demo_assets/contract_duarte.pdf` (fresh player, not in the squad)
- **Voice script:** `demo_assets/scout_note_duarte_script.txt`
- **Arc:** Home → **Genie One hero** → ingest (PDF + voice) → scout agent → Clip Search → 5 assistants → **FFP** → close

**The 4 Genie questions (escalation order):**
1. Which first-team players have **fewer than 18 months** left on their contract? *(structured)*
2. What is **Mateo Duarte's** release clause and when does his contract end? *(reads the just-uploaded PDF — the hero)*
3. What is our valuation of **Cristian Mosquera** and what does the scout report say? *(BLENDED + cited)*
4. In **Scenario B**, what's our squad value and who is highest injury risk? *(fused models)*

**Three rules if it wobbles:**
1. Genie returns nothing on a doc question → **Agent mode is off**, toggle it on.
2. App feels cold → click **Home** once first (scale-to-zero warm-up).
3. Never *create a new scenario then ask Genie about it* — ask about **Scenario B** (see gap note).

> **Honesty line (say it once, early):** "The app is live and deployed; the data's in real Delta tables and a real governed Volume. Some feeder data — wearables, opponent stats, transfer-fee history — is **synthetic but provider-shaped**, and every one is a **one-config swap** to the live feed. The only thing not deployed here is server-side transcription — one env var away."

---

## The run, beat by beat

### 0 · Cold open — it looks like their product · App ▸ Home · **2 min**
- **Click:** Open on **Home**. Point at the GPR donut, pinned Squad + Scouting summaries, activity feed.
- **Hook:** *"This is the front door my staff would actually log into — everything I know about my squad, live from the lakehouse."*
- **So what:** Frames the demo as **their product, not a Databricks console.**
- **Fallback:** Slow cards = valuation endpoint waking (scale-to-zero); talk over 5s, it warms on this click.

### 1 · ★ HERO — upload on laptop, ask on phone, cited · Squad ▸ Contracts → Genie One · **6 min**
- **Click:**
  1. **Squad ▸ Contracts** → under **"Upload a contract PDF"** drag in `contract_duarte.pdf` (a player *not* in the squad).
  2. On the **phone**, in **Genie One** (Acme Scout, **Agent mode ON**), ask *"What is Mateo Duarte's release clause and when does his contract end?"*
  3. It answers **€55M, 30 June 2029** with a **citation to the PDF you dropped 20 seconds ago**. Point at the citation.
- **Hook:** *"That PDF didn't go to a SaaS inbox — it landed inside my catalog, governed like any table. Seconds later, on my phone, my AI reads the actual signed contract and quotes it back to me with the source."*
- **So what:** The most important 90 seconds — **unstructured → governed → cited answer, cross-device, real time.** Answers "can I trust the AI?" live.
- **Tech truth:** UC Volume via Files API (table-grade governance); Genie **Agent mode** retrieval over the Volume + citation. `ai_parse_document`.
- **Verified:** Duarte PDF parses to `Mateo Duarte | 55.0 | 30 June 2029`; upload + Volume write confirmed through the deployed app.
- **Fallback:** Genie thin/generic → Agent mode OFF, toggle on. Phone network flaky → ask the same in the app's **Ask Acme AI** tab. Upload seems not to land → it did; re-ask Genie.

### 2 · Their UCO #1 — multimodal ingestion (voice half) · Scouting ▸ Scout Reports · **4 min**
- **Click:** **Scouting ▸ Scout Reports** → **● Record note** → read a few lines from `scout_note_duarte_script.txt` → stop. The app files it.
- **Hook:** *"My scout is pitchside in Argentina — he doesn't type a report, he talks. Seconds later that observation is a governed text file next to the contract and the ratings."*
- **So what:** PDF **and** voice both become governed, searchable, citable data — zero field friction.
- **Tech truth:** Both **audio** (`audio/*.wav`) **and** **transcript** (`transcripts/scout_note_*.txt`) land in the Volume.
- **Honesty:** Transcription = browser **Web Speech API** today; **one-env-var swap** (`TRANSCRIBE_ENDPOINT`) to **Whisper Model Serving**, no code change.
- **Fallback:** Mic blocked → say the one-env-var line and move on; 10 seeded scout notes already drive the next beat.

### 3 · Their UCO #2 — the scout agent (blended + cited) · Genie One / App ▸ Ask · **4 min**
- **Click:** The money question: *"What is our valuation of Cristian Mosquera and what does the latest scout report say about him?"* → valuation from the **table** + observation from the **transcript**, each cited. Then the structured under-18-months question for range.
- **Hook:** *"One question, plain English. It answers from my live numbers AND the actual scout's words, and shows me its sources. That's the difference between a chatbot and a knowledge assistant."*
- **So what:** One governed assistant across structured + unstructured, grounded and cited.
- **Tech truth:** Genie over **8 Delta tables + the documents Volume**; Agent mode = NL→SQL + file retrieval.
- **Fallback:** Doc answer thin → Agent mode toggle. Citation link slow → the answer names the source file; read it aloud.

### 4 · Scouting Clip Search — search the film · App ▸ Clip Search · **3 min**
- **Click:** Name: `Vini Jr`, then `Luis Diaz` (only that player). Description: `player in a red kit` (semantic grid). Videos play inline.
- **Hook:** *"My video archive used to be a folder nobody opened. Now I search it by name — dead accurate — or by what's happening on the pitch."*
- **So what:** Multimodal governed **video** search; two paths — *a name is a filter, not a vibe*; a description → embedding similarity.
- **Tech truth:** frame-sample (ffmpeg) → vision caption (`databricks-gpt-5-mini`) → embed (`gte-large-en`) → row in `clip_index`.
- **Fallback:** Odd card → still that player's own tagged clip. Video won't play → poster frame shows; next query.

---

## The five AI assistants — role-specific, all additive
*One governed platform, `ai_query`/Model Serving everywhere, synthetic feeds that swap to live with one config, every output explained or cited. Pace ~2 min each; land on FFP.*

### 5 · AI Transfer Assistant — interactive, explainable valuation · **2.5 min**
- **Click:** Open **Saka** (≈€146M). Drag **Goals /90** (value moves live, reason attached). Switch to **Raya (GK)** — sliders change to keeper drivers. **Recompute on Model Serving.**
- **Hook:** *"Valuation isn't one number, it's a conversation… position-aware, explainable to the last euro. A model I can defend in a negotiation."*
- **So what:** Explainable ML on Model Serving — additive pyfunc `value = peer base + Σ per-driver`, not a black box.
- **Honesty:** KPIs synthetic, Opta/StatsBomb-shaped (`player_kpis`) — one-config swap; production path = AutoML on historical fees.
- **Fallback:** First recompute lags = endpoint warm-up; UI already recomputed locally and they agree.

### 6 · AI Physio / Load Manager — minutes from wearables · **2 min**
- **Click:** Load board (most-at-risk first, R/A/G). Click a player → GPS + recovery sparklines → **Generate recommendation.**
- **Hook:** *"My sports scientists live in WHOOP and STATSports; my recruitment team lives in the ratings. Here they're the same platform… how many minutes to give him Saturday, with the reason."*
- **So what:** Operational fusion + live `ai_query` rationale grounded in the player's numbers.
- **Honesty:** WHOOP + STATSports synthetic (`load_status`); connector one-config swap (`notebooks/ingest_whoop.py`).
- **Fallback:** Recommendation slow (live FM) → narrate ACWR/minutes already on screen.

### 7 · AI Nutrition Assistant — fuelling from load + a voice note · **2 min**
- **Click:** Pick a player → type/record "prefers rice over pasta, lactose intolerant, big match Sunday" → **Generate fuelling plan.**
- **Hook:** *"A plan that already knows this player ran 77km last week and slept badly. The player just talks, and the plan adapts."*
- **So what:** Reuse — the physio data *and* the voice pipeline you already saw → structured-JSON plan via `ai_query`.
- **Honesty:** Metrics reuse the synthetic physio feed; voice = same browser Web-Speech pipeline.
- **Fallback:** Voice flaky → type the note; plan still adapts.

### 8 · AI Opposition / Match-Prep Analyst — brief with clip citations · **2 min**
- **Click:** Pick **Manchester City** → metrics strip (PPDA, xG, field tilt) → auto brief (hurt-us / beat-them / set-piece / **key battle**) with a **clip citation** (Rodri → real film).
- **Hook:** *"A whole analyst's afternoon in one click… when it says 'watch Rodri drop in and progress', it hands me the clip."*
- **So what:** The clip index cited from a second surface — data + film, one governed answer, with receipts.
- **Honesty:** Opponent metrics synthetic but provider-shaped (Opta/StatsBomb + SkillCorner) — one-config swap.
- **Fallback:** Brief slow (live FM) → talk the metrics strip; citation resolves deterministically.

### 9 · ★ FFP & Contracts — the board conversation (fills the Financials gap) · **3 min**
- **Click:** **FFP & Contracts** → verdict card (Compliant) → squad-cost ratio gauge vs 70% cap (≈62%) → PSR headroom → investment headroom → risk flags → economics table → **governed contract PDFs as evidence**. Note the old **Financials ▸ SOON** tab — this *is* that gap, filled.
- **Hook:** *"This is the conversation with the board… tells me how much I can actually spend this window — and every claim traces back to the signed PDF, governed in Unity Catalog."*
- **So what:** Ends on the exec-money question. Evidence cards pull the **FILE-column** table — governance down to the document.
- **Tech truth:** Real wages + contract dates; transparent amortization; verdict = live `ai_query`; evidence = `contract_files` (FILE) + `ai_parse_document`.
- **Honesty:** Club revenue/opex + acquisition fees are illustrative constants (one-config swap to the finance ledger); the model is transparent.
- **Fallback:** Verdict slow (live FM) → gauge/PSR/evidence are static-fast; present those.

### 🔒 30-second governance beat (drop in wherever they lean in)
- **Say:** *"Everything you've seen — tables, contract PDFs, voice notes, film — lives under **one Unity Catalog**. A Volume is governed exactly like a table: grants, lineage, audit. And this is **your account, isolated** — no data left the platform, nothing trained on anyone else's data, no cross-account bleed. That's what your security team will care about."*
- **Name-drop:** Unity Catalog · Volumes = table-grade governance · lineage + audit · per-account isolation · nothing leaves the platform.

### ✓ Close — tie it back · **1 min**
- **Say:** *"Four formats — numbers, contracts, voice, film — one governed platform. One AI assistant that answers across all of them **and cites its sources.** Operational writes and explainable models on the same data. That's the Data Intelligence Platform doing what a Sporting Director actually needs."*
- **If asked "real or mock?":** App **live and deployed**; **real Delta tables**; **real files in a real UC Volume**; **real footage** on real FM vision + embedding endpoints. Only not-deployed piece = server-side Whisper (one env var). Harness: **53/53**.

---

## Live vs synthetic — the honest map

| Component | Status | What's real / what's not |
|---|---|---|
| App + all endpoints (deployed) | **LIVE** | FastAPI + SPA on Databricks Apps, running as the app service principal. |
| players / contracts / scouting_targets / scout_reports | **LIVE** | Real Delta tables (20/14/7/10). Wages + contract dates are real. |
| Contract PDFs + scout transcripts in the Volume | **LIVE** | Real files in `acme_sports.demo.documents` (11 contracts, 10 transcripts); `ai_parse_document`+`ai_extract` pulled clause/date. |
| PDF upload → Volume (Squad ▸ Contracts) | **LIVE** | Verified through the deployed app; fresh Duarte PDF parses to €55M / 30-Jun-2029. |
| Voice note → audio + transcript in Volume | **LIVE** | Both land. **Transcription = browser Web Speech**; server Whisper = one-env-var swap (`TRANSCRIBE_ENDPOINT`). |
| Acme Scout (Genie Agent mode) | **LIVE** | Blended + cited over 8 tables + the Volume. |
| Clip Search (image + video) | **LIVE** | Real footage, real FM vision + embeddings; deterministic name resolver + semantic scene mode. |
| Lakebase scenario write (Squad ▸ Planning) | **LIVE** | App writes transactionally to Lakebase Postgres and reads back — verified through the app. |
| Valuation + Transfer models (Model Serving) | **LIVE** | Two serverless endpoints; served == local math. |
| Injury / valuation Delta scoring | **LIVE** | Scored into Delta (20 players), answerable in Genie. |
| player_kpis · load_status (WHOOP/STATSports) · opponents · contract_economics fees, club revenue/opex | **SYNTHETIC** | Provider-shaped, calibrated. Each a **one-config swap** to a live feed. Say so. |
| Server-side transcription (Whisper serving) | **NOT DEPLOYED** | Production path only — one env var. Browser Web Speech covers the live demo. |
| **App-created scenario → answerable in Genie** | **GAP — don't rely on it** | A scenario saved live writes to Lakebase but its Delta mirror **silently fails** (app SP has SELECT, not MODIFY, on the schema). Only pre-seeded **Scenario B** is in the Delta tables. **Ask Genie about Scenario B, never a scenario you just created.** |

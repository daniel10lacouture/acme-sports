# Decisions & Trade-offs

Why this build looks the way it does. Each decision is a real fork with a cost on the other side.

### 1. Genie Agent over a Knowledge Assistant
**Chose:** a Genie Space in **Agent mode** over the Delta tables *and* the attached documents Volume.
**Why:** Agent mode does retrieval over the Volume and returns answers **cited to the source file**,
and it's what the **Genie One mobile app** reaches — one assistant for structured + unstructured, on
the device the Sporting Director actually uses.
**Trade-off:** a Knowledge Assistant is stronger for pure document Q&A, but it wouldn't blend the
SQL numbers with the scout note in one cited answer, and isn't reachable from Genie One. We accepted
slightly weaker doc-only retrieval to get **blended, cited, mobile** answers.

### 2. Parse documents at query time — no content index
**Chose:** `ai_parse_document` / `ai_query` read the PDFs and transcripts **at query time**.
**Why:** a contract uploaded through the app is answerable **seconds later** — no re-index step, no
staleness. Freshness is the product.
**Trade-off:** higher per-query latency and token cost vs. a pre-built index. Acceptable at a squad's
document volume (tens–hundreds of files); at millions of docs we'd add an index and accept staleness.

### 3. Served valuation model with a local-coefficient fallback
**Chose:** the `acme-valuation` Model Serving endpoint (calibrated OLS, R²≈0.86), with the **exact
fitted coefficients embedded** in the app for local scoring if the endpoint is cold/unreachable.
**Why:** the interactive valuation sliders **never break** in a live demo or a real session; the badge
shows which path served the number, so it's honest.
**Trade-off:** the math lives in two places and must be kept in sync. We accepted that duplication to
buy resilience on the most-demoed surface.

### 4. Browser transcription now, Whisper Serving later
**Chose:** scout voice notes transcribe via the **browser Web Speech API** today; moving to a
**Whisper Model Serving** endpoint is a **one-environment-variable swap** (`TRANSCRIBE_ENDPOINT`).
**Why:** demonstrate the full multimodal capture flow with **zero GPU infra**, while showing the
exact production path — without pretending we deployed a model we didn't.
**Trade-off:** browser transcription is client-side and less accurate than Whisper. The design keeps
the *governance* identical (audio + transcript both land in the UC Volume) so only quality improves.

### 5. Real contract data, transparent illustrative finance
**Chose:** wages and contract dates are the **real** demo `contracts`/`players` data; acquisition
fees / revenue / opex used in the FFP model are **illustrative**, seeded deterministically.
**Why:** the demo never had purchase prices, so we compute amortization **transparently** (fee ÷
contract length) rather than hiding a black box. A production rollout points at the club's finance
ledger via one config change — every other column is already real.
**Trade-off:** the headline PSR numbers are modeled, not audited. We label this explicitly rather than
overclaim, which is also the honest thing to say to a CFO in the room.

### 6. Lakebase for interactive what-if, Delta for the rest
**Chose:** transfer-window "what-if" scenarios persist to **Lakebase** (transactional, low-latency
reads/writes); analytical tables stay in **Delta**.
**Why:** planning is an operational, read-modify-write loop that wants transactional semantics and
snappy reads — the operational-serving job Lakebase is built for. Delta remains the analytical source.
**Trade-off:** two stores to reason about. Justified by the workload split (operational vs. analytical).

### 7. FILE column type for governed contracts
**Chose:** `contract_files` uses the **FILE column type** so each governed PDF is a **row**, with
`ai_parse_document` reading the FILE and `ai_query` summarizing it as evidence.
**Trade-off:** a newer capability, but it keeps document governance *inside* the table model —
grants, lineage and audit apply to the doc exactly as they do to a column.

### 8. Synthetic / public data only
**Chose:** real footballers as **public figures**, a fictional club (**Acme Sports**), synthetic
wages/valuations. No customer data anywhere.
**Why:** demonstrates the pattern on realistic data while keeping the repo shareable and compliant.

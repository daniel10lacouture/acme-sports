# Genie One homepage branding — exact steps

**Not API-settable.** I probed the settings API, workspace-conf, and several endpoints —
Genie One homepage branding has **no public API** (confirmed against the docs, which give
UI steps only). Logo upload also requires the UI. So this is the one manual piece; all
assets are prepared below.

**Why your branding isn't showing yet:** nothing has been configured on the Appearance
page — the homepage is still on Databricks defaults. Follow the steps to apply it.

## Assets (ready)
- **Brand color:** `#2563EB` (blue — matches the real product app accent). *Alternative:* `#F5A623` amber if you prefer the marketing look.
- **Logo:** `brand/acme_logo.png` — the **real Acme Sports mark** (amber gradient ring + G), dark-G variant for light backgrounds. For a dark header use `brand/acme_logo_dark.png` (light-G variant). Sourced from acmesports.io.
- **Welcome markdown:** `brand/genie_one_welcome.md` (paste its contents)
- **Agent to pin:** **Acme Scout** — `space_id 01f19b59e604108aba34eda9d7e97569`
  (URL: https://fevm-classic-stable-9cgeia.cloud.databricks.com/genie/rooms/01f19b59e604108aba34eda9d7e97569)

## Steps — Appearance (workspace-level, applies to all users)
1. Top bar → your **username** → **Settings**.
2. Settings sidebar → **Appearance**.
3. Next to **Genie One home page** → **Edit**.
4. **Color:** set to `#2563EB` (blue, matches the product) — or `#F5A623` amber for the marketing look.
5. **Logo:** upload `brand/acme_logo.png`.
6. **Markdown text:** paste the contents of `brand/genie_one_welcome.md`.
7. **Save**.

## Steps — Pin the Acme Scout agent
8. Still under **Appearance** → next to **Genie home page** → **Edit**.
9. Toggle **Pinned content enabled** ON.
10. **Edit pinned assets** → **Select pinned assets** → choose **Acme Scout**.
11. **Save**.

## Optional — account-level (if you want it on the Databricks One / account home too)
- Username → **Settings** → **My preferences** tab → **Appearance preferences** →
  next to **Genie One home page** → **Edit** → apply the same color/logo/markdown/pins.

After saving, reopen Genie One on your phone — the blue theme, amber G logo, welcome
message, and pinned **Acme Scout** agent should appear.

# Acme Scout — Genie Space setup (M0)

**Workspace:** https://YOUR_WORKSPACE.cloud.databricks.com
**Warehouse:** Genie-Warehouse (`YOUR_WAREHOUSE_ID`)
**Table:** `acme_sports.demo.players`
**Volume (attach as source):** `acme_sports.demo.documents`

---

## Click-by-click

### 1. Create the space
1. Left sidebar → **Genie** (or go to `/genie`).
2. Top-right **+ New** → **New Genie space**.
3. Name it **`Acme Scout`**.
4. **SQL warehouse** → select **Genie-Warehouse**.

### 2. Add the structured table
5. In **Data** (or **Sources**) → **Add data / Add tables**.
6. Navigate `acme_sports` → `demo` → check **`players`** → **Confirm**.

### 3. Attach the documents volume  ← this is the "Analyze Files in Volumes" Beta
7. Still in **Sources**, click **Add** → choose **Files / Volume** (label may read "Unstructured files (Beta)" or "Documents").
8. Navigate `acme_sports` → `demo` → **`documents`** volume → **Add**.
   - If this option does NOT appear, the Beta is not enabled — see "Beta status" below.

### 4. Paste General Instructions
9. Open **Instructions** (pencil / "Instructions" tab) → paste the block from
   `genie_instructions.md` (also inline below) into **General instructions**.

### 5. Add Sample Questions
10. In **Sample questions**, add each line from `genie_sample_questions.txt`.

### 6. Save & note the space_id
11. Save. Copy the space ID from the URL: `/genie/rooms/<SPACE_ID>` — send it to me
    and I'll run the M0.5 blended-answer verification via the API.

---

## Beta status ("Analyze Files in Volumes with Genie Agents")
The preview toggle is **not readable via the public API** on this workspace (previews
endpoint returns Not Found; workspace-conf rejects guessed keys). Confirm it one of two ways:
- **Settings:** Settings → **Previews** → look for **"Genie"** / **"Analyze files"** /
  **"Documents in Genie / Genie Agents"** and ensure it's ON.
- **Functional test (definitive):** if step 7 above lets you attach the `documents`
  volume, the Beta is enabled.

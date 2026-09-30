#!/usr/bin/env bash
# WS4 fix — AI Transfer "Recompute on Model Serving" was silently falling back to local
# math because the app service principal got HTTP 403 querying the serving endpoint
# `acme-transfer-valuation` (it had never been granted CAN_QUERY — the L2 endpoint
# `acme-valuation` was granted in L5, but this later transfer endpoint was missed).
#
# Fix: grant CAN_QUERY on the endpoint to the app SP (client_id below). Merge (PATCH),
# so owner/admins are preserved. Idempotent.
set -euo pipefail
export DATABRICKS_AUTH_STORAGE=plaintext
P="YOUR_PROFILE"
APP_SP="47b731e0-6bf9-4ac4-923c-b93485795a4a"   # app-32gfki acme-sports
EPID=$(databricks serving-endpoints get acme-transfer-valuation -p "$P" -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
databricks permissions update serving-endpoints "$EPID" \
  --json "{\"access_control_list\":[{\"service_principal_name\":\"$APP_SP\",\"permission_level\":\"CAN_QUERY\"}]}" \
  -p "$P"
echo "Granted CAN_QUERY on acme-transfer-valuation ($EPID) to app SP $APP_SP"

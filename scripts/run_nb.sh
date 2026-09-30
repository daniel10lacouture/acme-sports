#!/usr/bin/env bash
# Import a local notebook .py and run it as a serverless one-time job; print its exit output.
# Usage: run_nb.sh <local_py> [run_name]
set -uo pipefail  # NOT -e: empty result_state greps during polling are expected
export DATABRICKS_AUTH_STORAGE=plaintext
P="fe-vm-classic-stable-9cgeia"
LOCAL="$1"
NAME="${2:-$(basename "$LOCAL" .py)}"
DIR="/Users/daniel.lacouture@databricks.com/acme_sports_l0"
NB="$DIR/$(basename "$LOCAL" .py)"
databricks workspace mkdirs "$DIR" -p $P >/dev/null 2>&1 || true
databricks workspace import "$NB" --file "$LOCAL" --language PYTHON --format SOURCE --overwrite -p $P >/dev/null
RID=$(databricks jobs submit --json "{\"run_name\":\"$NAME\",\"tasks\":[{\"task_key\":\"t\",\"notebook_task\":{\"notebook_path\":\"$NB\"}}]}" --no-wait -p $P -o json | python3 -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
echo "run_id=$RID  ($NAME)"
for i in $(seq 1 130); do
  J=$(databricks jobs get-run $RID -p $P -o json 2>/dev/null)
  LS=$(echo "$J" | grep '"life_cycle_state"' | head -1 | sed 's/.*: *"//;s/".*//')
  RS=$(echo "$J" | grep '"result_state"' | head -1 | sed 's/.*: *"//;s/".*//')
  if [ "$LS" = "TERMINATED" ] || [ "$LS" = "INTERNAL_ERROR" ] || [ "$LS" = "SKIPPED" ]; then break; fi
  sleep 12
done
echo "life=$LS result=$RS"
TID=$(databricks jobs get-run $RID -p $P -o json 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['tasks'][0]['run_id'])")
databricks jobs get-run-output $TID -p $P -o json 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
err=d.get('error')
if err: print('ERROR:',err); print((d.get('error_trace') or '')[:2500])
out=(d.get('notebook_output') or {}).get('result','')
if out: print('OUTPUT:',out[:3000])
"

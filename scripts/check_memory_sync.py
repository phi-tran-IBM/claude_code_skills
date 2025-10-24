import os, json, pathlib, sys
root = pathlib.Path(os.environ.get("TASK_DIR","."))
state = root/"artifacts"/"state.json"
sync  = root/"artifacts"/"memory_sync.json"
def die(m): print(f"[blocked] {m}"); sys.exit(1)

if not state.exists(): die(f"missing {state}")
if not sync.exists():  die(f"missing {sync}")
if sync.stat().st_mtime + 1 < state.stat().st_mtime: die("memory_sync older than state.json")

try:
    hdr = json.loads(sync.read_text())
except Exception as e:
    die(f"invalid JSON in memory_sync.json: {e}")

need = {"status","phase","task_id","AUTO","SAFE_MODE","DRY_RUN","cp_thresholds","memory_sync"}
if not need.issubset(hdr.keys()):
    die("memory_sync.json missing required fields")

print("[ok] memory sync")

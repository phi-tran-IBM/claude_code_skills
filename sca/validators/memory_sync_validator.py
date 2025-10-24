import json

def validate_memory_sync(tp) -> tuple[bool,str]:
    state = tp.artifacts/"state.json"
    sync  = tp.artifacts/"memory_sync.json"
    if not state.exists() or not sync.exists():
        return False, "memory sync: state.json or memory_sync.json missing"
    st = state.stat().st_mtime; sy = sync.stat().st_mtime
    if sy + 1 < st: return False, "memory_sync.json is older than state.json"
    try:
        hdr = json.loads(sync.read_text())
    except Exception as e:
        return False, f"memory_sync invalid JSON: {e}"
    need = {"status","phase","task_id","AUTO","SAFE_MODE","DRY_RUN","cp_thresholds","memory_sync"}
    if not need.issubset(hdr.keys()):
        return False, "memory_sync missing fields"
    return True, "memory sync ok"

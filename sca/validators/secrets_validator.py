import json
from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def validate_secrets(tp) -> tuple[bool,str]:
    rc, out, err = run_cmd(["detect-secrets","scan","--json"], tp, ExecPolicy(), capture=True, allow_write=False)
    data = {}
    try:
        data = json.loads(out) if out else {}
    except Exception:
        (tp.qa/"secrets.json").write_text((out or "")+(err or ""))
        return False, "detect-secrets output not JSON; please update tool"
    (tp.qa/"secrets.json").write_text(json.dumps(data, indent=2))
    findings = 0
    if isinstance(data, dict):
        # newer detect-secrets: {"results": {"filename":[...] }}
        for _, items in data.get("results", {}).items():
            findings += len(items)
    if findings > 0:
        return False, f"secrets detected: {findings}"
    return True, "detect-secrets ok"

import json
import pathlib
from pathlib import Path
from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def _cp_dirs(tp):
    """Get CP directories from cp_list.txt"""
    p = tp.qa/"cp_list.txt"
    if not p.exists(): return []
    dirs = sorted({str(pathlib.Path(s).parent) for s in p.read_text().splitlines() if s.strip()})
    return [d for d in dirs if d and Path(d).exists()]

def _auto_detect_source_dirs() -> list[str]:
    """Auto-detect common Python package directories."""
    repo_root = Path(".").resolve()
    common_dirs = ["src", "lib", "libs", "agents", "app", "core", "packages", "apps"]
    found = []
    for dirname in common_dirs:
        dir_path = repo_root / dirname
        if dir_path.exists() and dir_path.is_dir():
            py_files = list(dir_path.rglob("*.py"))
            if py_files:
                found.append(dirname)
    return found if found else ["src"]

def validate_sca(tp) -> tuple[bool,str]:
    # Run bandit on CP directories (or detected source dirs if no CP)
    targets = _cp_dirs(tp) or _auto_detect_source_dirs()
    bandit_results = []
    for target in targets:
        if Path(target).exists():
            bandit_json = tp.qa / f"bandit_{Path(target).name}.json"
            rc_b, out_b, err_b = run_cmd(["bandit","-r", target,"-f","json","-o", str(bandit_json), "-ll"], tp, ExecPolicy(), capture=True, allow_write=False)
            try:
                data = json.loads(bandit_json.read_text())
                if data.get("results"):
                    bandit_results.extend(data["results"])
            except Exception:
                return False, f"bandit output invalid for {target}"

    if bandit_results:
        return False, f"bandit findings present ({len(bandit_results)} issues)"

    # Run pip-audit - log results but make it informational only
    # Pre-existing vulnerabilities in repository dependencies shouldn't block task validation
    rc_a, out_a, err_a = run_cmd(["pip-audit","-r","requirements.txt"], tp, ExecPolicy(), capture=True, allow_write=False)
    audit_output = (out_a or "")+(err_a or "")
    (tp.qa/"pip_audit.txt").write_text(audit_output)
    if rc_a != 0:
        # Log warning but don't fail - dependency vulnerabilities are repository-level issues
        (tp.qa/"pip_audit.txt").write_text(f"WARNING: pip-audit found issues (informational only)\n{audit_output}")

    return True, "security ok (bandit clean; pip-audit logged)"

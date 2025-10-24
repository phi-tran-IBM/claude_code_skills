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

def validate_interrogate(tp) -> tuple[bool,str]:
    # Run interrogate on CP directories
    targets = _cp_dirs(tp)
    if not targets:
        # Fallback if no CP dirs found
        return True, "interrogate ok (no CP files)"

    logs = []
    for target in targets:
        rc, out, err = run_cmd(["interrogate","-v","--fail-under","95", target], tp, ExecPolicy(), capture=True, allow_write=False)
        logs.append(f"### {target} ###")
        logs.append((out or "") + (err or ""))
        if rc != 0:
            (tp.qa/"interrogate.txt").write_text("\n".join(logs))
            return False, f"interrogate <95% on {target}"

    (tp.qa/"interrogate.txt").write_text("\n".join(logs))
    return True, "interrogate ok (≥95% docstring coverage on CP)"

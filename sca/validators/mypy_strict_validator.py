import pathlib
from pathlib import Path
from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def _cp_dirs(tp):
    p = tp.qa/"cp_list.txt"
    if not p.exists(): return []
    dirs = sorted({str(pathlib.Path(s).parent) for s in p.read_text().splitlines() if s.strip()})
    return [d for d in dirs if d]

def _auto_detect_source_dirs() -> list[str]:
    """Auto-detect common Python package directories."""
    repo_root = Path(".").resolve()
    common_dirs = ["src", "lib", "libs", "agents", "app", "core", "packages", "apps", "sca_infrastructure"]
    found = []
    for dirname in common_dirs:
        dir_path = repo_root / dirname
        if dir_path.exists() and dir_path.is_dir():
            # Check if it has Python files
            py_files = list(dir_path.rglob("*.py"))
            if py_files:
                found.append(dirname)
    return found if found else ["src"]  # Fallback to src for backward compatibility

def validate_mypy(tp) -> tuple[bool,str]:
    policy = ExecPolicy()
    strict_targets = _cp_dirs(tp) or ["src/core"]
    logs = []
    for target in strict_targets:
        rc, out, err = run_cmd(["mypy","--strict", target], tp, policy, capture=True, allow_write=False)
        logs.append((out or "") + (err or ""))
        if rc != 0:
            (tp.qa/"mypy.txt").write_text("\n".join(logs))
            return False, f"mypy --strict failed on {target}"

    # Run mypy on detected source directories (non-strict for non-CP code)
    # NOTE: Non-CP mypy errors are informational only, not blocking
    source_dirs = _auto_detect_source_dirs()
    for src_dir in source_dirs:
        if Path(src_dir).exists():  # Only check if directory exists
            rc2, out2, err2 = run_cmd(["mypy", "--ignore-missing-imports", src_dir], tp, policy, capture=True, allow_write=False)
            logs.append(f"### Non-CP check: {src_dir} ###")
            logs.append((out2 or "") + (err2 or ""))
            # Non-CP errors are logged but don't fail the validation
            # Only CP files must pass mypy --strict per SCA protocol

    (tp.qa/"mypy.txt").write_text("\n".join(logs))
    return True, "mypy ok (CP files passed --strict)"

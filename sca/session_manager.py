import subprocess, pathlib, os, shlex
from .workspace_guard import TaskPaths

ALLOW = {"pytest","ruff","mypy","lizard","pip-audit","python","bash","git","detect-secrets","bandit","interrogate","pip"}

def run_cmd(cmd, tp: TaskPaths, policy, capture=True, allow_write=False):
    """
    SAFE/DRY enforcement + centralized run_log.
    - If SAFE_MODE=on and head not in allowlist -> block
    - If DRY_RUN=on and allow_write=True -> echo only
    """
    tp.qa.mkdir(parents=True, exist_ok=True)
    log = tp.qa / "run_log.txt"
    cmd_list = cmd if isinstance(cmd, list) else shlex.split(cmd)
    head = pathlib.Path(cmd_list[0]).name.lower()

    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n> {' '.join(cmd_list)}\n")

    if policy.safe_mode == "on" and head not in ALLOW:
        with log.open("a", encoding="utf-8") as f:
            f.write(f"[blocked] not allowed in SAFE_MODE: {head}\n")
        return 3, "", f"[blocked] not allowed: {head}"

    if policy.dry_run == "on" and allow_write:
        with log.open("a", encoding="utf-8") as f:
            f.write("[dry-run] skipped execution due to DRY_RUN\n")
        return 0, "[dry-run] skipped", ""

    p = subprocess.run(cmd_list, capture_output=capture, text=True)
    with log.open("a", encoding="utf-8") as f:
        f.write((p.stdout or "") + (p.stderr or ""))
    return p.returncode, p.stdout, p.stderr

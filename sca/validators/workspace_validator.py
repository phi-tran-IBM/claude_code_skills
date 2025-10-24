from pathlib import Path


REQUIRED_DIRS = ["context", "artifacts", "qa", "reports"]


def validate_workspace(tp) -> tuple[bool, str]:
    root: Path = tp.root
    missing = [d for d in REQUIRED_DIRS if not (root / d).exists()]
    if missing:
        return False, "Workspace: missing required dirs: " + ", ".join(missing)
    return True, "Workspace ok"


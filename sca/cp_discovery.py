import json, pathlib, fnmatch
from typing import List


def _unique_sorted(paths: List[pathlib.Path]) -> List[pathlib.Path]:
    seen = set()
    out: List[pathlib.Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return sorted(out)


def _match_globs(repo_root: pathlib.Path, patterns: List[str]) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    norm_patterns = [g.replace("\\", "/") for g in patterns]
    for p in repo_root.rglob("*.py"):
        up = str(p).replace("\\", "/")
        if any(fnmatch.fnmatch(up, patt) for patt in norm_patterns):
            files.append(p)
    return files


def discover_cp(task_dir: str) -> list[pathlib.Path]:
    base = pathlib.Path(task_dir)
    ctx = base / "context"
    cfg = ctx / "cp_paths.json"
    files: List[pathlib.Path] = []
    # default search root = repo working directory (".")
    repo_root = pathlib.Path(".")

    if cfg.exists():
        try:
            raw = json.loads(cfg.read_text(encoding="utf-8"))
            # Case 1: simple list of glob strings
            if isinstance(raw, list):
                patterns = [str(x) for x in raw if isinstance(x, str)]
                if patterns:
                    files.extend(_match_globs(repo_root, patterns))
            # Case 2: object schema with "paths": [ ... ]
            elif isinstance(raw, dict):
                paths = raw.get("paths", [])
                # Allow strings or objects inside paths
                for item in paths:
                    if isinstance(item, str):
                        files.extend(_match_globs(repo_root, [item]))
                    elif isinstance(item, dict):
                        if "file" in item and isinstance(item["file"], str):
                            fp = repo_root / item["file"]
                            if fp.exists():
                                files.append(fp)
                        # also accept "glob" or "pattern"
                        patt = item.get("glob") or item.get("pattern")
                        if isinstance(patt, str):
                            files.extend(_match_globs(repo_root, [patt]))
            # else: ignore unknown formats
        except Exception:
            # Fall through to default if parsing fails
            pass

    if not files:
        files = [p for p in repo_root.joinpath("src/core").rglob("*.py")]

    return _unique_sorted(files)

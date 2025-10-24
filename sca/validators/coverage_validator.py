import xml.etree.ElementTree as ET
from pathlib import Path
import json
import re
from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def _read_cp(tp):
    p = tp.qa/"cp_list.txt"
    if not p.exists(): return []
    return [Path(s.strip()) for s in p.read_text().splitlines() if s.strip()]


def _read_coverage_paths_from_pytest_ini(repo_root: Path) -> list[str]:
    """Extract --cov paths from pytest.ini addopts."""
    pytest_ini = repo_root / "pytest.ini"
    if not pytest_ini.exists():
        return []

    try:
        content = pytest_ini.read_text(encoding="utf-8")
        # Look for addopts section and extract --cov=<path> entries
        cov_paths = []
        for line in content.splitlines():
            line = line.strip()
            # Match --cov=path or --cov path patterns
            matches = re.findall(r'--cov[=\s]+([^\s]+)', line)
            cov_paths.extend(matches)
        return cov_paths
    except Exception:
        return []


def _read_coverage_paths_from_cp_config(task_dir: Path) -> list[str]:
    """Read explicit coverage_paths from cp_paths.json."""
    cp_config = task_dir / "context" / "cp_paths.json"
    if not cp_config.exists():
        return []

    try:
        data = json.loads(cp_config.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "coverage_paths" in data:
            paths = data["coverage_paths"]
            if isinstance(paths, list):
                return [str(p) for p in paths if isinstance(p, str)]
    except Exception:
        pass
    return []


def _auto_detect_source_dirs(repo_root: Path) -> list[str]:
    """Auto-detect common Python package directories."""
    common_dirs = ["src", "lib", "libs", "agents", "app", "core", "packages"]
    found = []
    for dirname in common_dirs:
        dir_path = repo_root / dirname
        if dir_path.exists() and dir_path.is_dir():
            # Check if it has Python files
            py_files = list(dir_path.rglob("*.py"))
            if py_files:
                found.append(dirname)
    return found


def _resolve_coverage_paths(repo_root: Path, task_dir: Path) -> list[str]:
    """
    Resolve coverage paths using cascading fallback strategy.

    Priority order:
    1. Read from pytest.ini (respects project config)
    2. Read from cp_paths.json (task-specific override)
    3. Auto-detect common directories
    4. Fallback to "src" (backwards compatible)
    """
    # Try pytest.ini first
    paths = _read_coverage_paths_from_pytest_ini(repo_root)
    if paths:
        return paths

    # Try cp_paths.json
    paths = _read_coverage_paths_from_cp_config(task_dir)
    if paths:
        return paths

    # Try auto-detection
    paths = _auto_detect_source_dirs(repo_root)
    if paths:
        return paths

    # Fallback to "src" for backwards compatibility
    return ["src"]


def validate_coverage(tp) -> tuple[bool,str]:
    # Resolve coverage paths using cascading strategy
    # Get repo root from task_dir structure (task_dir/../..)
    repo_root = Path(tp.root).parent.parent.resolve()
    task_dir = tp.root
    cov_paths = _resolve_coverage_paths(repo_root, task_dir)

    # Build pytest command with detected coverage paths
    # Write coverage.xml to task-specific qa/ directory
    cov_xml_path = tp.qa / "coverage.xml"
    cmd = ["pytest"]
    for path in cov_paths:
        cmd.extend(["--cov", path])
    cmd.extend(["--cov-branch", f"--cov-report=xml:{cov_xml_path}", "-q"])

    rc, out, err = run_cmd(cmd, tp, ExecPolicy(), capture=True, allow_write=False)
    (tp.qa/"coverage.txt").write_text((out or "") + (err or ""))
    cov_xml = tp.qa/"coverage.xml"
    if not cov_xml.exists():
        return False, "coverage.xml missing"

    cp_files = _read_cp(tp)
    if not cp_files:
        return False, "coverage: CP list missing (cp_list.txt)"

    try:
        tree = ET.parse(cov_xml); root = tree.getroot()
    except Exception as e:
        return False, f"coverage: invalid XML ({e})"

    totals = {"l_cov":0,"l_tot":0,"b_cov":0,"b_tot":0}
    cp_norm = set(str(p.resolve()).replace("\\","/") for p in cp_files)

    # Extract source paths from coverage.xml
    sources = []
    for source_elem in root.findall(".//sources/source"):
        if source_elem.text:
            sources.append(Path(source_elem.text.strip()))

    matched_files = []  # Track which files matched for debugging
    class_branch_rates = []  # Track branch rates for weighted average

    for clazz in root.findall(".//class"):
        fname = clazz.get("filename","")
        # Try to resolve filename using source paths from coverage.xml
        fpath = None
        if sources:
            for src in sources:
                candidate = src / fname
                if candidate.exists():
                    fpath = str(candidate.resolve()).replace("\\","/")
                    break
        # Fallback to direct resolution if no sources or file not found
        if not fpath:
            fpath = str(Path(fname).resolve()).replace("\\","/")

        if fpath not in cp_norm:
            continue

        matched_files.append(fpath)  # Track matched file
        lines_cov=0; lines_tot=0
        # coverage.py XML: lines/line @hits; branch details optional
        for line in clazz.findall(".//lines/line"):
            lines_tot += 1
            if int(line.get("hits","0"))>0:
                lines_cov += 1
        totals["l_cov"] += lines_cov
        totals["l_tot"] += lines_tot

        # Extract branch rate from this class (not global)
        br_attr = clazz.get("branch-rate")
        if br_attr is not None:
            class_branch_rates.append((float(br_attr), lines_tot))
    if totals["l_tot"] == 0:
        debug_msg = f"No lines counted. Matched files: {matched_files}, CP files: {list(cp_norm)}"
        return False, f"coverage: no lines counted for CP files. Debug: {debug_msg}"

    # Debug output
    debug_info = f"Matched {len(matched_files)} CP files: {matched_files}. Lines: {totals['l_cov']}/{totals['l_tot']}"
    (tp.qa/"coverage_debug.txt").write_text(debug_info)

    line_rate = totals["l_cov"]/totals["l_tot"]

    # Calculate weighted average branch rate for CP files only
    if class_branch_rates:
        total_weighted_branch = sum(rate * weight for rate, weight in class_branch_rates)
        total_weight = sum(weight for _, weight in class_branch_rates)
        branch_rate = total_weighted_branch / total_weight if total_weight > 0 else line_rate
    else:
        # Fallback to line_rate if no branch data available
        branch_rate = line_rate

    if line_rate < 0.95 or branch_rate < 0.95:
        return False, f"coverage below threshold: line={line_rate:.3f}, branch={branch_rate:.3f}"
    return True, f"coverage ok: line={line_rate:.3f}, branch={branch_rate:.3f}"

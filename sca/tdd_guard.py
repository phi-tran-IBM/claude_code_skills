import re, pathlib
from .cp_discovery import discover_cp

def run_tdd_guard(task_dir: str) -> list[str]:
    marker = re.compile(r"@pytest\.mark\.cp\b")
    hypoth = re.compile(r"@given\(")
    errors = []

    cp_files = discover_cp(task_dir)
    test_files = [p for p in pathlib.Path("tests").rglob("*.py")]

    def refs(txt:str, cp:pathlib.Path):
        return cp.stem in txt

    for cp in cp_files:
        has_marker = has_prop = False
        newest_test = 0.0
        for t in test_files:
            try:
                txt = t.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if refs(txt, cp):
                if marker.search(txt): has_marker = True
                if hypoth.search(txt): has_prop = True
                newest_test = max(newest_test, t.stat().st_mtime)
        if not has_marker: errors.append(f"{cp}: missing @pytest.mark.cp")
        if not has_prop:   errors.append(f"{cp}: missing Hypothesis @given property")
        if newest_test == 0.0 or cp.stat().st_mtime > newest_test:
            errors.append(f"{cp}: code newer than tests (write tests first)")
    return errors

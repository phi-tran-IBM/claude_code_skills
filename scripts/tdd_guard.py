"""
TDD Guard: enforces discipline on the Critical Path (CP).

Hard checks:
1) CP tests must use @pytest.mark.cp (marker presence).
2) Each CP module must have >=1 Hypothesis property test referencing it.
3) Modified CP module cannot be newer (mtime) than its nearest CP test.

Outputs "[ok] ..." on success, "[blocked] ..." with causes on failure.
"""
import pathlib, sys, re, subprocess

def fail(msgs):
    if isinstance(msgs, str): msgs=[msgs]
    for m in msgs: print(f"[blocked] {m}")
    sys.exit(1)

def ok(msg):
    print(f"[ok] {msg}")
    sys.exit(0)

root = pathlib.Path(".")
cp_list = subprocess.check_output(
    [sys.executable, "scripts/discover_cp.py"], text=True
).strip().splitlines()
cp_files = [pathlib.Path(p) for p in cp_list if p.strip()]

if not cp_files:
    fail("no CP files discovered (check src/core or context/cp_paths.json)")

test_files = [p for p in root.rglob("tests/**/*.py")] + [p for p in root.rglob("tests/*.py")]

marker_probe = re.compile(r"@pytest\.mark\.cp\b")
hypothesis_probe = re.compile(r"@given\(")

def references_module(test_text, cp_path):
    stem = cp_path.stem
    return (stem in test_text)

def candidate_tests_for(cp):
    c = []
    for t in test_files:
        if t.name.startswith(f"test_{cp.stem}") or t.stem.endswith(cp.stem):
            c.append(t)
    return c if c else test_files

missing_marker, missing_hypothesis, mtime_violations = [], [], []

for cp in cp_files:
    cand = candidate_tests_for(cp)
    if not cand:
        missing_marker.append(f"{cp}: no tests found")
        missing_hypothesis.append(f"{cp}: no tests found")
        mtime_violations.append(f"{cp}: no tests found")
        continue

    has_marker, has_hyp, newest_test_mtime = False, False, 0.0
    for t in cand:
        try:
            txt = t.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if references_module(txt, cp):
            if marker_probe.search(txt): has_marker = True
            if hypothesis_probe.search(txt): has_hyp = True
        newest_test_mtime = max(newest_test_mtime, t.stat().st_mtime)

    if not has_marker:
        missing_marker.append(f"{cp}: missing @pytest.mark.cp in CP tests")
    if not has_hyp:
        missing_hypothesis.append(f"{cp}: missing >=1 Hypothesis @given property test")

    if cp.stat().st_mtime > newest_test_mtime:
        mtime_violations.append(f"{cp}: code newer than CP tests (write tests first)")

errors = missing_marker + missing_hypothesis + mtime_violations
if errors:
    fail(errors)
ok("TDD Guard passed: marker, property, and mtime rules satisfied")

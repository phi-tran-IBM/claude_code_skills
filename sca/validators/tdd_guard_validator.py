from ..tdd_guard import run_tdd_guard

def validate_tdd_guard(tp) -> tuple[bool,str]:
    errs = run_tdd_guard(str(tp.root))
    if errs: return False, "TDD Guard failed: " + "; ".join(errs[:8])
    return True, "TDD Guard ok"

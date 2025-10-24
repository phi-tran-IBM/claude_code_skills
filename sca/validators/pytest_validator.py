from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def validate_pytest(tp) -> tuple[bool,str]:
    rc, out, err = run_cmd(["pytest","-q","--maxfail=1"], tp, ExecPolicy(), capture=True, allow_write=False)
    (tp.qa/"pytest.txt").write_text((out or "") + (err or ""))
    return (rc==0, "pytest ok" if rc==0 else "pytest failed (see qa/pytest.txt)")

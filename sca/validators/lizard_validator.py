from ..session_manager import run_cmd
from ..execution_policy import ExecPolicy

def validate_lizard(tp) -> tuple[bool,str]:
    rc, out, err = run_cmd(["lizard","-x","tests","-o", str(tp.qa/"lizard_report.txt"), "src"], tp, ExecPolicy(), capture=True, allow_write=False)
    return (rc==0, "lizard ok" if rc==0 else "lizard failed thresholds")

from .validators.workspace_validator import validate_workspace
from .validators.context_gate import validate_context_gate
from .validators.cp_discovery_validator import validate_cp_discovery
from .validators.tdd_guard_validator import validate_tdd_guard
from .validators.pytest_validator import validate_pytest
from .validators.coverage_validator import validate_coverage
from .validators.mypy_strict_validator import validate_mypy
from .validators.lizard_validator import validate_lizard
from .validators.interrogate_validator import validate_interrogate
from .validators.secrets_validator import validate_secrets
from .validators.sca_security_validator import validate_sca
from .validators.memory_sync_validator import validate_memory_sync
from .validators.traceability_validator import validate_traceability

def run_validators(task_paths, include_context=True, include_cp=True, include_qa=True, include_memory=True, include_traceability=True, tracker=None):
    checks = []
    # Always check workspace first
    checks += [("workspace", validate_workspace)]
    if include_context: checks += [("context_gate", validate_context_gate)]
    if include_cp:      checks += [("cp_discovery", validate_cp_discovery), ("tdd_guard", validate_tdd_guard)]
    if include_qa:      checks += [("pytest", validate_pytest), ("coverage", validate_coverage),
                                   ("mypy", validate_mypy), ("lizard", validate_lizard),
                                   ("interrogate", validate_interrogate), ("secrets", validate_secrets),
                                   ("security", validate_sca)]
    if include_memory:  checks += [("memory_sync", validate_memory_sync)]
    if include_traceability: checks += [("traceability", validate_traceability)]

    results = {}
    for name, chk in checks:
        if tracker:
            tracker.log_event("validator", name, "start")

        ok, msg = chk(task_paths)
        results[name] = ok

        if tracker:
            tracker.log_event("validator", name, "pass" if ok else "fail", {"message": msg})

        if not ok:
            return {"status":"blocked","failure":msg, "checks": results}
    return {"status":"ok", "checks": results}

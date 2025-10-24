import json, os
from typing import Dict, List

def current_header_from_env() -> Dict:
    task_id = os.environ.get("TASK_ID","999-unset") + "-" + os.environ.get("TASK_SLUG","unset")
    return {
      "agent": "SCA",
      "protocol_version": "13.7",
      "status": "ok",
      "phase": os.environ.get("phase","context"),
      "task_id": task_id,
      "AUTO": int(os.environ.get("AUTO","2")),
      "SAFE_MODE": os.environ.get("SAFE_MODE","on"),
      "DRY_RUN": os.environ.get("DRY_RUN","off"),
      "tools_available": ["pytest","pytest-cov","hypothesis","mypy","lizard","ruff","interrogate","bandit","detect-secrets","pip-audit","python","git"],
      "cp_thresholds": {
        "coverage_line": 0.95,
        "coverage_branch": 0.95,
        "mypy_strict_errors_cp": 0,
        "lizard_ccn_max": 10,
        "lizard_cognitive_max": 15,
        "docs_coverage_cp": 0.95
      },
      "gates": {
        "workspace": "pending",
        "context": "pending",
        "tdd": "pending",
        "coverage_cp": "pending",
        "types_cp": "pending",
        "complexity": "pending",
        "docs_cp": "pending",
        "security": "pending",
        "hygiene": "pending",
        "authenticity_ast": "pending",
        "performance": "pending",
        "fuzz": "pending",
        "data_integrity": "pending",
        "traceability": "pending"
      },
      "cp_coverage": {"line": 0.0, "branch": 0.0},
      "deliverables": [],
      "validation_artifacts": [
        {"name":"Coverage","artifact_path":"qa/coverage.xml"},
        {"name":"Mypy","artifact_path":"qa/mypy.txt"},
        {"name":"Lizard","artifact_path":"qa/lizard_report.txt"},
        {"name":"Docs","artifact_path":"qa/interrogate.txt"},
        {"name":"Secrets","artifact_path":"qa/secrets.json"},
        {"name":"Bandit","artifact_path":"qa/bandit.json"},
        {"name":"PipAudit","artifact_path":"qa/pip_audit.txt"}
      ],
      "run": {
        "run_id": "<will be set by tracker>",
        "session_id": "<will be set by tracker>",
        "task_dir": os.environ.get("TASK_DIR", ""),
        "log": "qa/run_log.txt",
        "manifest": "artifacts/run_manifest.json",
        "events": "artifacts/run_events.jsonl"
      },
      "next_actions": [],
      "memory_sync": {
        "canonical_spec": os.environ.get("SCA_CANONICAL_PROTOCOL",""),
        "write_to": "<TASK_DIR>\\artifacts\\memory_sync.json",
        "resume_hint": "load <TASK_DIR>\\artifacts\\state.json if present"
      }
    }

def print_header(hdr: Dict, notes: List[str], self_checks: List[str], next_actions: List[str]):
    out = json.dumps(hdr, indent=2)
    print(out)
    print("\n---\nNotes:")
    for n in notes[:10]: print(f"- {n}")
    print("Self-Checks:")
    for s in self_checks: print(f"- {s}")
    print("Next Actions:")
    for a in next_actions[:5]: print(f"- {a}")

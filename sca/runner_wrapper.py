import os
from .execution_policy import ExecPolicy
from .workspace_guard import TaskPaths
from .protocol_loader import exists_and_wins
from .snapshot_manager import SnapshotManager
from .validator_chain import run_validators
from .output_contract import current_header_from_env, print_header
from .dci_enforcer import ensure_determinism
from .session_tracker import get_or_create_tracker
from .cp_discovery import discover_cp

PHASES = ["context","1","2","3","4","5"]

def run(task_dir: str, phase: str, auto: str, safe_mode: str, dry_run: str):
    tp = TaskPaths(task_dir); tp.ensure()
    policy = ExecPolicy.from_strings(auto, safe_mode, dry_run)

    # Initialize session tracker
    tracker = get_or_create_tracker(task_dir)
    tracker.log_event("entrypoint", "run-phase", "start", {"phase": phase, "auto": auto})

    hdr = current_header_from_env()
    hdr["phase"] = phase if phase in PHASES or phase=="auto" else "context"
    hdr["status"] = "ok"
    hdr["run"] = tracker.get_run_info()

    if not exists_and_wins():
        hdr["status"]="blocked"
        tracker.log_event("authority", "protocol_check", "fail", {"reason": "canonical protocol not found"})
        print_header(hdr, ["Canonical protocol file not found"], ["authority check failed"], ["Create protocol file"])
        return

    ensure_determinism(tp)

    # Discover CP files for run context
    cp_files = [str(p) for p in discover_cp(task_dir)]

    # Write run context
    tracker.write_run_context(
        task_id=hdr.get("task_id", "unknown"),
        phase=hdr["phase"],
        tools=hdr.get("tools_available", []),
        cp_files=cp_files
    )

    plan = PHASES if phase=="auto" else [phase]
    for ph in plan:
        os.environ["phase"] = ph
        hdr["phase"] = ph
        tracker.log_event("phase", ph, "start")

        if ph == "context":
            res = run_validators(tp, include_context=True, include_cp=False, include_qa=False, include_memory=False, tracker=tracker)
        elif ph in ("1","2"):
            res = run_validators(tp, include_context=True, include_cp=False, include_qa=False, include_memory=True, tracker=tracker)
        elif ph == "3":
            res = run_validators(tp, include_context=False, include_cp=True, include_qa=False, include_memory=True, tracker=tracker)
        else:
            res = run_validators(tp, include_context=False, include_cp=True, include_qa=True, include_memory=True, tracker=tracker)

        if res["status"] != "ok":
            hdr["status"]="blocked"
            tracker.log_event("phase", ph, "blocked", {"failure": res.get("failure","unknown")})
            print_header(hdr, [f"Phase {ph} blocked"], [res.get("failure","unknown")], ["See failure & fix files"])
            # Write manifest even on failure
            tracker.write_run_manifest()
            return

        tracker.log_event("phase", ph, "complete")
        SnapshotManager(task_dir).snapshot_save(hdr, ph)

        if not policy.allow_multi_phase() and phase=="auto" and ph not in ("context","1"):
            break

    # Write run manifest at completion
    tracker.write_run_manifest()
    tracker.log_event("entrypoint", "run-phase", "complete", {"phase": hdr["phase"]})
    print_header(hdr, [f"Phase {hdr['phase']} complete"], ["validators ok","snapshot saved"], ["Proceed next phase"])

import json, pathlib, time
from typing import Dict
from .workspace_guard import TaskPaths, assert_task_scoped_write

class SnapshotManager:
    def __init__(self, task_dir: str):
        self.tp = TaskPaths(task_dir); self.tp.ensure()

    def _generate_compliance_status(self, header: Dict) -> None:
        """Generate compliance_status.md with gate results and evidence links."""
        gates = header.get("gates", {})
        status_lines = ["# Compliance Status", "", "| Gate | Status | Evidence |", "|---|---|---|"]

        evidence_map = {
            "coverage_cp": "qa/coverage.xml",
            "types_cp": "qa/mypy.txt",
            "security": "qa/bandit.json, qa/secrets.json",
            "docs_cp": "qa/interrogate.txt",
            "complexity": "qa/lizard_report.txt",
            "traceability": "artifacts/run_manifest.json"
        }

        for gate, status in gates.items():
            evidence = evidence_map.get(gate, "qa/run_log.txt")
            status_lines.append(f"| {gate} | {status} | {evidence} |")

        (self.tp.artifacts / "compliance_status.md").write_text("\n".join(status_lines))

    def _claims_index(self):
        # Compact claims map from evidence.json if present
        ev = self.tp.context / "evidence.json"
        claims = []
        if ev.exists():
            try:
                data = json.loads(ev.read_text())
                for i,e in enumerate(data,1):
                    claims.append({
                        "id": f"C-{i:02d}",
                        "source_type": e.get("source_type"),
                        "url_or_doi": e.get("url_or_doi"),
                        "claim": (e.get("synthesized_finding") or e.get("claim") or "")[:160]
                    })
            except Exception:
                pass
        return claims

    def snapshot_save(self, header: Dict, phase_hint: str):
        # state.json
        state = {"phase": header.get("phase", phase_hint), "status": header.get("status","ok"),
                 "task_id": header.get("task_id",""), "ts": time.time(),
                 "AUTO": header.get("AUTO"), "SAFE_MODE": header.get("SAFE_MODE"), "DRY_RUN": header.get("DRY_RUN")}
        p_state = self.tp.artifacts/"state.json"; assert_task_scoped_write(p_state, self.tp)
        p_state.write_text(json.dumps(state, indent=2))

        # memory_sync.json mirror
        p_sync = self.tp.artifacts/"memory_sync.json"; assert_task_scoped_write(p_sync, self.tp)
        p_sync.write_text(json.dumps(header, indent=2))

        # artifacts/index.md
        (self.tp.artifacts/"index.md").write_text("| tag | path | one-liner |\n|---|---|---|\n")

        # executive summary
        exec_sum = self.tp.context/"executive_summary.md"
        if not exec_sum.exists():
            exec_sum.write_text("# Executive Summary [SUM]\n")
        with exec_sum.open("a", encoding="utf-8") as f:
            f.write(f"- Phase {phase_hint} saved at {time.ctime()}\n")

        # Generate compliance status
        self._generate_compliance_status(header)

        # claims_index.json
        (self.tp.context/"claims_index.json").write_text(json.dumps(self._claims_index(), indent=2))

        # phase snapshot
        (self.tp.reports/f"{phase_hint}_snapshot.md").write_text(f"# Snapshot {phase_hint}\n\nSaved at {time.ctime()}\n")

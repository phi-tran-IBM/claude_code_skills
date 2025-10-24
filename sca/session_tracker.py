"""
Session and Run ID tracking for SCA Protocol Skill.

Implements traceability requirements from full_protocol.md §11:
- run_id: unique identifier per skill invocation
- session_id: persistent identifier per task (correlates multiple runs)
- run_context.json: metadata about current run
- run_manifest.json: pointers to QA artifacts
- run_events.jsonl: append-only event stream
"""

from __future__ import annotations
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionTracker:
    """Manages session and run tracking for a task."""

    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir).resolve()
        self.artifacts_dir = self.task_dir / "artifacts"
        self.qa_dir = self.task_dir / "qa"

        # Get project ID from path structure
        self.project_root = self.task_dir.parent.parent
        self.project_id = self.project_root.name

        # Ensure directories exist
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.qa_dir.mkdir(parents=True, exist_ok=True)

        # Session ID: persistent per task WITH project prefix
        self.session_id = self._load_or_create_session_id()

        # Run ID: unique per invocation
        self.run_id = self._generate_run_id()

        # Paths to traceability artifacts
        self.run_log_path = self.qa_dir / "run_log.txt"
        self.run_context_path = self.artifacts_dir / "run_context.json"
        self.run_manifest_path = self.artifacts_dir / "run_manifest.json"
        self.run_events_path = self.artifacts_dir / "run_events.jsonl"

    def _load_or_create_session_id(self) -> str:
        """Load existing session ID or create new one."""
        session_file = self.artifacts_dir / "session_id.txt"

        if session_file.exists():
            try:
                session_id = session_file.read_text(encoding="utf-8").strip()
                if session_id:
                    return session_id
            except Exception:
                pass

        # Create new session ID with project prefix
        session_id = f"{self.project_id}-{uuid.uuid4()}"
        session_file.write_text(session_id, encoding="utf-8")
        return session_id

    def _generate_run_id(self) -> str:
        """Generate unique run ID for this invocation."""
        # Format: timestamp-uuid (sortable + unique)
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{timestamp}-{short_uuid}"

    def log_event(
        self,
        kind: str,
        name: str,
        status: str = "",
        detail: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Append event to run_events.jsonl.

        Args:
            kind: Event type (e.g., "entrypoint", "validator", "phase")
            name: Event name (e.g., "run-phase", "context_gate", "context")
            status: Event status (e.g., "start", "complete", "fail", "blocked")
            detail: Additional event details
        """
        event = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "session_id": self.session_id,
            "run_id": self.run_id,
            "kind": kind,
            "name": name,
            "status": status,
            "detail": detail or {}
        }

        with self.run_events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    def write_run_context(
        self,
        task_id: str,
        phase: str,
        tools: List[str],
        cp_files: Optional[List[str]] = None,
        data_sources: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Write run_context.json with metadata about current run.

        Required by protocol §11.
        """
        context = {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "task_id": task_id,
            "task_dir": str(self.task_dir),
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tools": tools,
            "cp_files": cp_files or [],
            "data_sources": data_sources or [],
            "config": config or {},
            "environment": {
                "AUTO": os.environ.get("AUTO", "2"),
                "SAFE_MODE": os.environ.get("SAFE_MODE", "on"),
                "DRY_RUN": os.environ.get("DRY_RUN", "off"),
                "SCA_SKILL_PATH": os.environ.get("SCA_SKILL_PATH", ""),
                "SCA_CANONICAL_PROTOCOL": os.environ.get("SCA_CANONICAL_PROTOCOL", "")
            }
        }

        self.run_context_path.write_text(
            json.dumps(context, indent=2, separators=(",", ": ")),
            encoding="utf-8"
        )

    def write_run_manifest(
        self,
        qa_artifacts: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """
        Write run_manifest.json with pointers to QA artifacts.

        Required by protocol §11.
        """
        manifest = {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "artifacts": qa_artifacts or self._discover_qa_artifacts()
        }

        self.run_manifest_path.write_text(
            json.dumps(manifest, indent=2, separators=(",", ": ")),
            encoding="utf-8"
        )

    def _discover_qa_artifacts(self) -> List[Dict[str, str]]:
        """Discover existing QA artifacts in qa/ directory."""
        artifacts = []

        artifact_patterns = {
            "coverage": "coverage.xml",
            "pytest": "pytest.txt",
            "mypy": "mypy.txt",
            "lizard": "lizard_report.txt",
            "interrogate": "interrogate.txt",
            "secrets": "secrets.json",
            "bandit": "bandit.json",
            "pip_audit": "pip_audit.txt",
            "run_log": "run_log.txt",
            "cp_list": "cp_list.txt"
        }

        for name, filename in artifact_patterns.items():
            artifact_path = self.qa_dir / filename
            if artifact_path.exists():
                artifacts.append({
                    "name": name,
                    "path": str(artifact_path.relative_to(self.task_dir)),
                    "size_bytes": artifact_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        artifact_path.stat().st_mtime
                    ).isoformat() + "Z"
                })

        return artifacts

    def get_run_info(self) -> Dict[str, str]:
        """Get current run information for output contract."""
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "task_dir": str(self.task_dir),
            "log": str(self.run_log_path.relative_to(self.task_dir)),
            "manifest": str(self.run_manifest_path.relative_to(self.task_dir)),
            "events": str(self.run_events_path.relative_to(self.task_dir))
        }


def get_or_create_tracker(task_dir: str | Path) -> SessionTracker:
    """
    Get or create a SessionTracker for the given task directory.

    This is the main entry point for other modules.
    """
    return SessionTracker(task_dir)

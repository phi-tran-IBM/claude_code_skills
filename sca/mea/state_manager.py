"""
MEA State Manager - Track MEA execution state across attempts.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class MEAStateManager:
    """
    Manages MEA execution state and history.
    Tracks attempts, fixes applied, and validation results.
    """

    def __init__(self, task_dir: Path):
        """
        Initialize state manager.

        Args:
            task_dir: Path to the task directory
        """
        self.task_dir = Path(task_dir)
        self.artifacts_dir = self.task_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.artifacts_dir / "mea_state.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """
        Load existing MEA state or create new.

        Returns:
            State dictionary
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                return self._create_new_state()
        else:
            return self._create_new_state()

    def _create_new_state(self) -> Dict[str, Any]:
        """
        Create a new MEA state.

        Returns:
            New state dictionary
        """
        return {
            "session_id": self._generate_session_id(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "current_attempt": 0,
            "max_attempts": 3,
            "status": "in_progress",
            "attempts": [],
            "total_files_written": 0,
            "total_fixes_applied": 0,
            "validation_gates": {}
        }

    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID for this MEA cycle.

        Returns:
            Session ID string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        import uuid
        short_uuid = str(uuid.uuid4())[:8]
        return f"mea-{timestamp}-{short_uuid}"

    def record_attempt(self, validation_result: Dict[str, Any], fixes_attempted: List[str]) -> None:
        """
        Record an MEA attempt.

        Args:
            validation_result: Result from validation
            fixes_attempted: List of fix categories attempted
        """
        self.state["current_attempt"] += 1

        # Extract gate results
        gates = {}
        if "checks" in validation_result:
            for gate, passed in validation_result["checks"].items():
                gates[gate] = "pass" if passed else "fail"

        attempt_record = {
            "attempt_number": self.state["current_attempt"],
            "timestamp": datetime.utcnow().isoformat(),
            "validation_status": validation_result.get("status", "unknown"),
            "gates": gates,
            "failure_message": validation_result.get("failure", ""),
            "fixes_attempted": fixes_attempted,
            "files_modified": []  # Can be populated if tracking file changes
        }

        self.state["attempts"].append(attempt_record)
        self.state["updated_at"] = datetime.utcnow().isoformat()

        # Update gate tracking
        for gate, status in gates.items():
            if gate not in self.state["validation_gates"]:
                self.state["validation_gates"][gate] = []
            self.state["validation_gates"][gate].append({
                "attempt": self.state["current_attempt"],
                "status": status
            })

        self._save_state()

    def record_files_written(self, files: List[str]) -> None:
        """
        Record files written during MEA execution.

        Args:
            files: List of file paths written
        """
        self.state["total_files_written"] += len(files)

        if self.state["attempts"]:
            # Add to most recent attempt
            self.state["attempts"][-1]["files_written"] = files

        self.state["updated_at"] = datetime.utcnow().isoformat()
        self._save_state()

    def record_fixes_applied(self, fixes: Dict[str, str]) -> None:
        """
        Record fixes applied during MEA execution.

        Args:
            fixes: Dictionary of file paths to fixed content
        """
        self.state["total_fixes_applied"] += len(fixes)

        if self.state["attempts"]:
            # Add to most recent attempt
            self.state["attempts"][-1]["files_modified"] = list(fixes.keys())

        self.state["updated_at"] = datetime.utcnow().isoformat()
        self._save_state()

    def mark_complete(self, status: str) -> None:
        """
        Mark MEA cycle as complete.

        Args:
            status: Final status ("ok", "failed", "abandoned")
        """
        self.state["status"] = status
        self.state["completed_at"] = datetime.utcnow().isoformat()
        self.state["updated_at"] = datetime.utcnow().isoformat()

        # Calculate summary statistics
        self.state["summary"] = self._generate_summary()

        self._save_state()

    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics for the MEA cycle.

        Returns:
            Summary dictionary
        """
        summary = {
            "total_attempts": self.state["current_attempt"],
            "final_status": self.state["status"],
            "duration_seconds": None,
            "gates_passed": [],
            "gates_failed": [],
            "persistent_failures": []
        }

        # Calculate duration if possible
        if "completed_at" in self.state:
            start = datetime.fromisoformat(self.state["created_at"])
            end = datetime.fromisoformat(self.state["completed_at"])
            summary["duration_seconds"] = (end - start).total_seconds()

        # Analyze gate results
        if self.state["attempts"]:
            last_attempt = self.state["attempts"][-1]
            for gate, status in last_attempt.get("gates", {}).items():
                if status == "pass":
                    summary["gates_passed"].append(gate)
                else:
                    summary["gates_failed"].append(gate)

        # Find persistent failures (failed in all attempts)
        for gate, history in self.state["validation_gates"].items():
            if all(h["status"] == "fail" for h in history):
                summary["persistent_failures"].append(gate)

        return summary

    def get_state(self) -> Dict[str, Any]:
        """
        Get current MEA state.

        Returns:
            Current state dictionary
        """
        return self.state.copy()

    def get_current_attempt(self) -> int:
        """
        Get current attempt number.

        Returns:
            Current attempt (1-based)
        """
        return self.state["current_attempt"]

    def is_max_attempts_reached(self) -> bool:
        """
        Check if maximum attempts have been reached.

        Returns:
            True if max attempts reached
        """
        return self.state["current_attempt"] >= self.state["max_attempts"]

    def get_last_validation_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the last validation result.

        Returns:
            Last validation result or None
        """
        if self.state["attempts"]:
            return self.state["attempts"][-1]
        return None

    def get_gate_history(self, gate_name: str) -> List[Dict[str, Any]]:
        """
        Get history for a specific validation gate.

        Args:
            gate_name: Name of the validation gate

        Returns:
            List of attempt results for this gate
        """
        return self.state["validation_gates"].get(gate_name, [])

    def _save_state(self) -> None:
        """Save state to JSON file."""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2)

    def reset(self) -> None:
        """Reset MEA state for a new cycle."""
        self.state = self._create_new_state()
        self._save_state()

    def export_report(self) -> str:
        """
        Export a human-readable report of the MEA cycle.

        Returns:
            Formatted report string
        """
        report_lines = [
            "# MEA Execution Report",
            f"\nSession ID: {self.state['session_id']}",
            f"Status: {self.state['status']}",
            f"Total Attempts: {self.state['current_attempt']}/{self.state['max_attempts']}",
            f"Files Written: {self.state['total_files_written']}",
            f"Fixes Applied: {self.state['total_fixes_applied']}",
            "\n## Attempts\n"
        ]

        for attempt in self.state["attempts"]:
            report_lines.append(f"### Attempt {attempt['attempt_number']}")
            report_lines.append(f"- Timestamp: {attempt['timestamp']}")
            report_lines.append(f"- Status: {attempt['validation_status']}")

            if attempt.get("gates"):
                report_lines.append("- Gates:")
                for gate, status in attempt["gates"].items():
                    emoji = "✅" if status == "pass" else "❌"
                    report_lines.append(f"  - {gate}: {emoji} {status}")

            if attempt.get("fixes_attempted"):
                report_lines.append(f"- Fixes Attempted: {', '.join(attempt['fixes_attempted'])}")

            report_lines.append("")

        if "summary" in self.state:
            summary = self.state["summary"]
            report_lines.append("\n## Summary\n")
            report_lines.append(f"- Final Status: {summary['final_status']}")
            if summary["duration_seconds"]:
                report_lines.append(f"- Duration: {summary['duration_seconds']:.2f} seconds")
            if summary["gates_passed"]:
                report_lines.append(f"- Gates Passed: {', '.join(summary['gates_passed'])}")
            if summary["gates_failed"]:
                report_lines.append(f"- Gates Failed: {', '.join(summary['gates_failed'])}")
            if summary["persistent_failures"]:
                report_lines.append(f"- Persistent Failures: {', '.join(summary['persistent_failures'])}")

        return "\n".join(report_lines)
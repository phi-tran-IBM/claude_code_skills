"""
MEA Orchestrator - Bridges code generation with validation.
Enables the Write → Validate → Fix → Repeat loop.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sca.workspace_guard import TaskPaths
from sca.validator_chain import run_validators
from sca.session_tracker import get_or_create_tracker
from .failure_parser import FailureParser
from .fix_generator import FixGenerator
from .state_manager import MEAStateManager


class MEAOrchestrator:
    """
    Orchestrates the full MEA cycle: Write → Validate → Fix → Repeat.
    """

    def __init__(self, task_dir: str, skill_path: str = None):
        """
        Initialize MEA orchestrator.

        Args:
            task_dir: Path to the task directory
            skill_path: Path to the SCA skill (for imports)
        """
        self.task_dir = Path(task_dir)
        self.task_paths = TaskPaths(task_dir)
        self.task_paths.ensure()

        # Initialize components
        self.failure_parser = FailureParser()
        self.fix_generator = FixGenerator()
        self.state_manager = MEAStateManager(self.task_dir)
        self.tracker = get_or_create_tracker(task_dir)

        # Add skill path to sys.path if provided
        if skill_path:
            sys.path.insert(0, skill_path)

    def write_code_batch(self, code_batch: Dict[str, str]) -> Dict[str, Any]:
        """
        Write a batch of code files to the task directory.

        Args:
            code_batch: Dictionary mapping relative file paths to content

        Returns:
            Dictionary with write results
        """
        self.tracker.log_event("mea", "write_batch", "start", {"files": list(code_batch.keys())})

        written_files = []
        errors = []

        for rel_path, content in code_batch.items():
            try:
                # Resolve path relative to task directory
                file_path = self.task_dir / rel_path

                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the file
                file_path.write_text(content, encoding='utf-8')
                written_files.append(str(rel_path))

                self.tracker.log_event("mea", "write_file", "success", {"file": rel_path})
            except Exception as e:
                error_msg = f"Failed to write {rel_path}: {str(e)}"
                errors.append(error_msg)
                self.tracker.log_event("mea", "write_file", "error", {"file": rel_path, "error": str(e)})

        result = {
            "written_files": written_files,
            "errors": errors,
            "status": "ok" if not errors else "partial"
        }

        self.tracker.log_event("mea", "write_batch", "complete", result)
        return result

    def execute_validation(self) -> Dict[str, Any]:
        """
        Execute the full validation chain.

        Returns:
            Validation results dictionary
        """
        self.tracker.log_event("mea", "validation", "start")

        # Run validators
        result = run_validators(
            task_paths=self.task_paths,
            include_context=True,
            include_cp=True,
            include_qa=True,
            include_memory=True,
            include_traceability=True,
            tracker=self.tracker
        )

        # Add run information
        result["run"] = self.tracker.get_run_info()

        self.tracker.log_event("mea", "validation", "complete", {"status": result.get("status")})

        return result

    def parse_failures(self, validation_result: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Parse validation failures into actionable fixes.

        Args:
            validation_result: Result from execute_validation

        Returns:
            Dictionary of gate names to list of required fixes
        """
        return self.failure_parser.parse_validation_output(validation_result)

    def apply_fixes(self, failures: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Generate and apply fixes for validation failures.

        Args:
            failures: Parsed failures from parse_failures

        Returns:
            Dictionary of fixed file paths to content
        """
        self.tracker.log_event("mea", "apply_fixes", "start", {"gates_to_fix": list(failures.keys())})

        fixed_files = self.fix_generator.generate_fixes(failures, self.task_dir)

        # Write the fixed files
        for file_path, content in fixed_files.items():
            full_path = self.task_dir / file_path
            full_path.write_text(content, encoding='utf-8')
            self.tracker.log_event("mea", "fix_applied", "success", {"file": file_path})

        self.tracker.log_event("mea", "apply_fixes", "complete", {"files_fixed": len(fixed_files)})

        return fixed_files

    def execute_mea_cycle(self, code_batch: Dict[str, str], attempt: int = 1, max_attempts: int = 3) -> Dict[str, Any]:
        """
        Execute a full MEA cycle with auto-fix capability.

        Args:
            code_batch: Dictionary of files to write
            attempt: Current attempt number
            max_attempts: Maximum attempts before giving up

        Returns:
            MEA result dictionary
        """
        self.tracker.log_event("mea", "cycle", "start", {"attempt": attempt, "max_attempts": max_attempts})

        # Write code batch
        write_result = self.write_code_batch(code_batch)

        if write_result["status"] != "ok":
            return {
                "agent": "SCA",
                "protocol_version": "13.8",
                "mea_attempt": attempt,
                "status": "write_failed",
                "errors": write_result["errors"]
            }

        # Execute validation
        validation_result = self.execute_validation()

        # Build MEA result
        mea_result = {
            "agent": "SCA",
            "protocol_version": "13.8",
            "mea_attempt": attempt,
            "max_attempts": max_attempts,
            "validation": validation_result,
            "status": validation_result["status"]
        }

        # If validation passed, we're done
        if validation_result["status"] == "ok":
            self.state_manager.record_attempt(validation_result, [])
            self.state_manager.mark_complete("ok")
            mea_result["message"] = "Validation passed - ready for snapshot"

        # If validation failed, parse failures and prepare remediation
        else:
            failures = self.parse_failures(validation_result)
            mea_result["remediation"] = failures

            # Record attempt
            self.state_manager.record_attempt(validation_result, list(failures.keys()))

            # Check if we should auto-fix
            if attempt < max_attempts:
                mea_result["next_action"] = "auto_fix"
                mea_result["message"] = f"Validation failed on attempt {attempt}/{max_attempts} - fixes identified"
            else:
                self.state_manager.mark_complete("failed")
                mea_result["message"] = f"Validation failed after {max_attempts} attempts - manual intervention required"

        self.tracker.log_event("mea", "cycle", "complete", {"status": mea_result["status"]})

        # Write manifest
        self.tracker.write_run_manifest()

        return mea_result

    def get_state(self) -> Dict[str, Any]:
        """
        Get current MEA state.

        Returns:
            Current state dictionary
        """
        return self.state_manager.get_state()


def get_or_create_orchestrator(task_dir: str) -> MEAOrchestrator:
    """
    Factory function to get or create an MEA orchestrator.

    Args:
        task_dir: Task directory path

    Returns:
        MEAOrchestrator instance
    """
    skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
    return MEAOrchestrator(task_dir, skill_path)
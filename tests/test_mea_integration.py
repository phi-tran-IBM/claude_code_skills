"""
Integration tests for MEA (Mandatory Execution Algorithm) implementation.
"""

import json
import tempfile
from pathlib import Path
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sca.mea.orchestrator import MEAOrchestrator
from sca.mea.failure_parser import FailureParser
from sca.mea.fix_generator import FixGenerator
from sca.mea.state_manager import MEAStateManager


class TestMEAOrchestrator:
    """Test MEA orchestrator functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary task directory
        self.temp_dir = tempfile.mkdtemp()
        self.task_dir = Path(self.temp_dir) / "tasks" / "001-test"
        self.task_dir.mkdir(parents=True)

        # Create required subdirectories
        (self.task_dir / "context").mkdir()
        (self.task_dir / "artifacts").mkdir()
        (self.task_dir / "qa").mkdir()
        (self.task_dir / "reports").mkdir()

        # Initialize orchestrator
        self.orchestrator = MEAOrchestrator(str(self.task_dir))

    def test_write_code_batch(self):
        """Test writing code batch to files."""
        code_batch = {
            "src/test.py": "def test(): pass",
            "tests/test_test.py": "def test_it(): assert True"
        }

        result = self.orchestrator.write_code_batch(code_batch)

        assert result["status"] == "ok"
        assert len(result["written_files"]) == 2
        assert "src/test.py" in result["written_files"]

        # Verify files were created
        test_file = self.task_dir / "src" / "test.py"
        assert test_file.exists()
        assert test_file.read_text() == "def test(): pass"

    def test_write_code_batch_with_errors(self):
        """Test error handling in code batch writing."""
        # Try to write to an invalid path
        code_batch = {
            "/absolute/path/not/allowed.py": "content"
        }

        result = self.orchestrator.write_code_batch(code_batch)

        # Should handle the error gracefully
        assert result["status"] == "partial" or len(result["errors"]) > 0


class TestFailureParser:
    """Test failure parsing functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.parser = FailureParser()

    def test_parse_tdd_failures(self):
        """Test parsing TDD guard failures."""
        output = {
            "status": "blocked",
            "failure": "TDD Guard: tests/test_module.py missing @pytest.mark.cp",
            "checks": {"tdd_guard": False}
        }

        failures = self.parser.parse_validation_output(output)

        assert "tdd_guard" in failures
        assert any("@pytest.mark.cp" in fix for fix in failures["tdd_guard"])

    def test_parse_placeholder_failures(self):
        """Test parsing placeholder violations."""
        output = {
            "status": "blocked",
            "failure": "placeholders found in CP: src/module.py:10 - found 'TODO'",
            "checks": {"placeholders": False}
        }

        failures = self.parser.parse_validation_output(output)

        assert "placeholders" in failures
        assert any("TODO" in fix for fix in failures["placeholders"])

    def test_parse_coverage_failures(self):
        """Test parsing coverage failures."""
        output = {
            "status": "blocked",
            "failure": "coverage 85.5% below threshold 95%",
            "checks": {"coverage": False}
        }

        failures = self.parser.parse_validation_output(output)

        assert "coverage" in failures
        assert any("85.5%" in fix and "95%" in fix for fix in failures["coverage"])

    def test_parse_multiple_failures(self):
        """Test parsing multiple gate failures."""
        output = {
            "status": "blocked",
            "failure": "Multiple failures: TDD Guard failed, coverage below threshold",
            "checks": {
                "tdd_guard": False,
                "coverage": False,
                "placeholders": True
            }
        }

        failures = self.parser.parse_validation_output(output)

        assert "tdd_guard" in failures
        assert "coverage" in failures
        assert "placeholders" not in failures  # Only failed gates


class TestFixGenerator:
    """Test fix generation functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.generator = FixGenerator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_add_pytest_mark_cp(self):
        """Test adding @pytest.mark.cp decorator."""
        content = """import pytest

def test_something():
    assert True"""

        fixed = self.generator._add_pytest_mark_cp(content)

        assert "@pytest.mark.cp" in fixed
        assert fixed.count("@pytest.mark.cp") == 1

    def test_add_hypothesis_test(self):
        """Test adding Hypothesis property test."""
        content = """import pytest

def test_something():
    assert True"""

        fixed = self.generator._add_hypothesis_test(content)

        assert "from hypothesis import given" in fixed
        assert "@given" in fixed
        assert "st.integers()" in fixed

    def test_remove_placeholders(self):
        """Test removing placeholder comments."""
        # Create a file with placeholders
        test_file = self.temp_dir / "test.py"
        test_file.write_text("""def process():
    # TODO: Implement this
    # FIXME: Handle errors
    pass  # PLACEHOLDER
""")

        failures = {
            "placeholders": [f"Remove TODO at {test_file}"]
        }

        fixes = self.generator.generate_fixes(failures, self.temp_dir)

        # Should generate fixed content without placeholders
        assert any("TODO" not in content for content in fixes.values())

    def test_fix_stub_functions(self):
        """Test fixing stub functions."""
        content = """def calculate():
    pass

def process():
    return None"""

        fixed = self.generator._fix_stub_functions(content)

        assert "pass" not in fixed or "Basic implementation" in fixed
        assert "return result" in fixed


class TestMEAStateManager:
    """Test MEA state management."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = MEAStateManager(self.temp_dir)

    def test_create_new_state(self):
        """Test creating new MEA state."""
        state = self.manager.get_state()

        assert state["current_attempt"] == 0
        assert state["max_attempts"] == 3
        assert state["status"] == "in_progress"
        assert "session_id" in state

    def test_record_attempt(self):
        """Test recording validation attempt."""
        validation_result = {
            "status": "blocked",
            "checks": {
                "tdd_guard": False,
                "coverage": True
            },
            "failure": "TDD violations"
        }

        self.manager.record_attempt(validation_result, ["tdd_guard"])

        state = self.manager.get_state()
        assert state["current_attempt"] == 1
        assert len(state["attempts"]) == 1
        assert state["attempts"][0]["validation_status"] == "blocked"

    def test_max_attempts_check(self):
        """Test maximum attempts checking."""
        assert not self.manager.is_max_attempts_reached()

        # Record 3 attempts
        for i in range(3):
            self.manager.record_attempt({"status": "blocked"}, [])

        assert self.manager.is_max_attempts_reached()

    def test_mark_complete(self):
        """Test marking MEA cycle as complete."""
        self.manager.record_attempt({"status": "ok", "checks": {}}, [])
        self.manager.mark_complete("ok")

        state = self.manager.get_state()
        assert state["status"] == "ok"
        assert "completed_at" in state
        assert "summary" in state

    def test_export_report(self):
        """Test exporting human-readable report."""
        # Record some attempts
        self.manager.record_attempt(
            {"status": "blocked", "checks": {"tdd_guard": False}},
            ["tdd_guard"]
        )
        self.manager.record_attempt(
            {"status": "ok", "checks": {"tdd_guard": True}},
            []
        )
        self.manager.mark_complete("ok")

        report = self.manager.export_report()

        assert "MEA Execution Report" in report
        assert "Session ID:" in report
        assert "Attempt 1" in report
        assert "Attempt 2" in report
        assert "Final Status: ok" in report


class TestMEAIntegration:
    """Full integration tests for MEA cycle."""

    @pytest.mark.skip(reason="Requires full environment setup")
    def test_full_mea_cycle(self):
        """Test complete MEA cycle from bad code to passing."""
        temp_dir = Path(tempfile.mkdtemp())
        task_dir = temp_dir / "tasks" / "001-test"
        task_dir.mkdir(parents=True)

        orchestrator = MEAOrchestrator(str(task_dir))

        # Start with code that has issues
        bad_code = {
            "src/calc.py": "def add(x, y): return x + y  # TODO: add validation",
            "tests/test_calc.py": "def test_add(): assert True"
        }

        # First attempt should identify issues
        result = orchestrator.execute_mea_cycle(bad_code, attempt=1)

        assert result["status"] == "blocked"
        assert "remediation" in result
        assert result["mea_attempt"] == 1

        # Check state was recorded
        state = orchestrator.get_state()
        assert state["current_attempt"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
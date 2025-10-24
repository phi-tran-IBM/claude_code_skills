"""
Failure Parser - Parse validation failures into actionable fixes.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path


class FailureParser:
    """
    Parse validation failures and extract specific remediation actions.
    """

    def parse_validation_output(self, output: Dict) -> Dict[str, List[str]]:
        """
        Parse validation failures into specific remediation actions.

        Args:
            output: Validation output dictionary from run_validators

        Returns:
            Dictionary mapping gate names to lists of required fixes
        """
        failures = {}

        if output.get('status') != 'ok':
            failure_msg = output.get('failure', '')
            checks = output.get('checks', {})

            # Parse each failed gate
            for gate, passed in checks.items():
                if not passed:
                    gate_fixes = self._parse_gate_failure(gate, failure_msg)
                    if gate_fixes:
                        failures[gate] = gate_fixes

            # Also parse the main failure message
            general_fixes = self._parse_failure_message(failure_msg)
            if general_fixes:
                failures['general'] = general_fixes

        return failures

    def _parse_gate_failure(self, gate: str, failure_msg: str) -> List[str]:
        """
        Parse failures for a specific gate.

        Args:
            gate: Name of the failed gate
            failure_msg: Full failure message

        Returns:
            List of fixes for this gate
        """
        fixes = []

        if gate == 'tdd_guard':
            fixes.extend(self._parse_tdd_failures(failure_msg))
        elif gate == 'coverage':
            fixes.extend(self._parse_coverage_failures(failure_msg))
        elif gate == 'placeholders':
            fixes.extend(self._parse_placeholder_failures(failure_msg))
        elif gate == 'mypy':
            fixes.extend(self._parse_type_failures(failure_msg))
        elif gate == 'context_gate':
            fixes.extend(self._parse_context_failures(failure_msg))
        elif gate == 'ast':
            fixes.extend(self._parse_ast_failures(failure_msg))
        elif gate == 'pytest':
            fixes.extend(self._parse_pytest_failures(failure_msg))

        return fixes

    def _parse_failure_message(self, msg: str) -> List[str]:
        """
        Parse general failure message for common patterns.

        Args:
            msg: Failure message

        Returns:
            List of general fixes
        """
        fixes = []

        # Extract file-specific issues
        file_pattern = r'([^\s]+\.py):\s*(.+?)(?:;|$|\n)'
        matches = re.findall(file_pattern, msg, re.IGNORECASE)
        for file_path, issue in matches:
            fixes.append(f"Fix {issue.strip()} in {file_path}")

        return fixes

    def _parse_tdd_failures(self, msg: str) -> List[str]:
        """Parse TDD Guard failures."""
        fixes = []

        # Missing @pytest.mark.cp
        if 'missing @pytest.mark.cp' in msg.lower():
            files = re.findall(r'([^\s]+test[^\s]*\.py)', msg)
            for f in set(files):
                fixes.append(f"Add @pytest.mark.cp decorator to tests in {f}")

        # Missing Hypothesis @given
        if 'missing.*@given' in msg.lower() or 'hypothesis' in msg.lower():
            files = re.findall(r'([^\s]+test[^\s]*\.py)', msg)
            for f in set(files):
                fixes.append(f"Add Hypothesis @given property test to {f}")

        # Missing failure path test
        if 'failure.?path' in msg.lower() or 'failure test' in msg.lower():
            files = re.findall(r'([^\s]+test[^\s]*\.py)', msg)
            for f in set(files):
                fixes.append(f"Add failure-path test (with pytest.raises) to {f}")

        # Code newer than tests
        if 'newer than.*test' in msg.lower():
            match = re.search(r'([^\s]+\.py).*newer', msg, re.IGNORECASE)
            if match:
                fixes.append(f"Write tests before implementing {match.group(1)}")

        return fixes

    def _parse_coverage_failures(self, msg: str) -> List[str]:
        """Parse coverage failures."""
        fixes = []

        # Coverage below threshold
        match = re.search(r'coverage.*?(\d+(?:\.\d+)?)\s*%.*?below.*?(\d+)\s*%', msg, re.IGNORECASE)
        if match:
            current = float(match.group(1))
            required = float(match.group(2))
            fixes.append(f"Increase test coverage from {current}% to {required}%")

        # Uncovered lines
        uncovered_pattern = r'([^\s]+\.py).*?lines?\s+(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)'
        matches = re.findall(uncovered_pattern, msg, re.IGNORECASE)
        for file_path, lines in matches:
            fixes.append(f"Add tests for uncovered lines {lines} in {file_path}")

        return fixes

    def _parse_placeholder_failures(self, msg: str) -> List[str]:
        """Parse placeholder violations."""
        fixes = []

        # Extract placeholder locations
        placeholder_pattern = r'([^\s]+\.py):(\d+).*?(TODO|FIXME|PLACEHOLDER|HARDCODED)'
        matches = re.findall(placeholder_pattern, msg, re.IGNORECASE)

        for file_path, line_num, placeholder_type in matches:
            fixes.append(f"Remove {placeholder_type} at {file_path}:{line_num}")

        # General placeholder message
        if not matches and any(word in msg.upper() for word in ['TODO', 'FIXME', 'PLACEHOLDER']):
            fixes.append("Remove all TODO/FIXME/PLACEHOLDER markers from CP files")

        return fixes

    def _parse_type_failures(self, msg: str) -> List[str]:
        """Parse mypy type checking failures."""
        fixes = []

        # Missing type hints
        if 'missing type' in msg.lower() or 'no type hint' in msg.lower():
            files = re.findall(r'([^\s]+\.py)', msg)
            for f in set(files):
                fixes.append(f"Add type hints to {f}")

        # Type errors
        type_error_pattern = r'([^\s]+\.py):(\d+).*?error:?\s*(.+?)(?:\[|$|\n)'
        matches = re.findall(type_error_pattern, msg, re.IGNORECASE)
        for file_path, line_num, error in matches:
            fixes.append(f"Fix type error at {file_path}:{line_num} - {error.strip()}")

        return fixes

    def _parse_context_failures(self, msg: str) -> List[str]:
        """Parse context gate failures."""
        fixes = []

        # Missing files
        missing_pattern = r'missing[/:]?\s*([^\s,]+\.(?:md|json))'
        matches = re.findall(missing_pattern, msg, re.IGNORECASE)
        for file_name in matches:
            fixes.append(f"Create required context file: context/{file_name}")

        # Empty files
        empty_pattern = r'empty[:]?\s*([^\s,]+\.(?:md|json))'
        matches = re.findall(empty_pattern, msg, re.IGNORECASE)
        for file_name in matches:
            fixes.append(f"Add content to context/{file_name}")

        # Evidence requirements
        if 'evidence.json' in msg and 'P1 sources' in msg:
            match = re.search(r'needs?\s*>=?\s*(\d+)\s*P1\s*sources?', msg)
            if match:
                fixes.append(f"Add at least {match.group(1)} P1 priority sources to evidence.json")

        return fixes

    def _parse_ast_failures(self, msg: str) -> List[str]:
        """Parse AST validator failures."""
        fixes = []

        # Stub functions
        stub_pattern = r'stub.*?([^\s]+\.py):(\w+)'
        matches = re.findall(stub_pattern, msg, re.IGNORECASE)
        for file_path, func_name in matches:
            fixes.append(f"Implement non-stub body for {func_name}() in {file_path}")

        # General stub message
        if 'stub function' in msg.lower() and not matches:
            fixes.append("Replace all stub functions with real implementations")

        return fixes

    def _parse_pytest_failures(self, msg: str) -> List[str]:
        """Parse pytest execution failures."""
        fixes = []

        # Test failures
        failed_pattern = r'FAILED\s+([^\s]+::test_\w+)'
        matches = re.findall(failed_pattern, msg)
        for test_path in matches:
            fixes.append(f"Fix failing test: {test_path}")

        # Import errors
        if 'ImportError' in msg or 'ModuleNotFoundError' in msg:
            module_pattern = r"(?:ImportError|ModuleNotFoundError).*?'(\w+)'"
            matches = re.findall(module_pattern, msg)
            for module in matches:
                fixes.append(f"Fix import error for module: {module}")

        # Syntax errors
        if 'SyntaxError' in msg:
            syntax_pattern = r'([^\s]+\.py):(\d+)'
            matches = re.findall(syntax_pattern, msg)
            for file_path, line_num in matches:
                fixes.append(f"Fix syntax error at {file_path}:{line_num}")

        return fixes

    def categorize_fixes(self, failures: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Categorize fixes by action type for easier processing.

        Args:
            failures: Dictionary of gate failures to fixes

        Returns:
            Dictionary categorized by action type (add_file, modify_file, etc.)
        """
        categorized = {
            'add_file': [],
            'modify_file': [],
            'add_test': [],
            'fix_syntax': [],
            'add_content': []
        }

        for gate, fixes in failures.items():
            for fix in fixes:
                if 'Create' in fix or 'create' in fix:
                    categorized['add_file'].append(fix)
                elif 'Add test' in fix or '@pytest.mark.cp' in fix or '@given' in fix:
                    categorized['add_test'].append(fix)
                elif 'Fix syntax' in fix or 'SyntaxError' in fix:
                    categorized['fix_syntax'].append(fix)
                elif 'Add content' in fix or 'empty' in fix:
                    categorized['add_content'].append(fix)
                else:
                    categorized['modify_file'].append(fix)

        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
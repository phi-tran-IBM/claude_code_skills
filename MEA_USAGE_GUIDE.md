# MEA (Mandatory Execution Algorithm) Usage Guide

## Overview

The MEA implementation provides automated code generation, validation, and fix cycles for the SCA Protocol Skill. It implements the Write→Validate→Fix→Repeat loop with intelligent failure parsing and automatic remediation suggestions.

## Quick Start

### 1. Create a New Task

```powershell
# Create a task for your MEA cycle
.\commands\new-task.ps1 -TaskId 001 -TaskSlug my-feature
```

### 2. Prepare Your Code Batch

Create a JSON object with file paths as keys and content as values:

```powershell
$code = @{
    "src/core/calculator.py" = @"
def add(x: int, y: int) -> int:
    '''Add two numbers.'''
    return x + y
"@
    "tests/test_calculator.py" = @"
import pytest
from hypothesis import given, strategies as st
from src.core.calculator import add

@pytest.mark.cp
@given(st.integers(), st.integers())
def test_add(x, y):
    assert add(x, y) == x + y

@pytest.mark.cp
def test_add_failure():
    with pytest.raises(TypeError):
        add("not", "int")
"@
} | ConvertTo-Json -Compress
```

### 3. Execute MEA Cycle

```powershell
# First attempt
.\commands\mea-cycle.ps1 -CodeBatch $code -Attempt 1

# If validation fails, the output will show required fixes
# Apply fixes and retry
.\commands\mea-cycle.ps1 -CodeBatch $fixedCode -Attempt 2

# Maximum 3 attempts
.\commands\mea-cycle.ps1 -CodeBatch $finalCode -Attempt 3
```

### 4. Handle Results

The MEA cycle returns JSON with the following structure:

```json
{
    "agent": "SCA",
    "protocol_version": "13.8",
    "mea_attempt": 1,
    "max_attempts": 3,
    "status": "ok|blocked|error",
    "validation": { /* Full validation results */ },
    "remediation": { /* If blocked, specific fixes needed */ },
    "message": "Human-readable status message"
}
```

## Common Validation Gates and Fixes

### TDD Guard Failures

**Issue:** Missing test decorators or property tests
```json
"remediation": {
    "tdd_guard": [
        "Add @pytest.mark.cp decorator to tests in tests/test_module.py",
        "Add Hypothesis @given property test to tests/test_module.py",
        "Add failure-path test (with pytest.raises) to tests/test_module.py"
    ]
}
```

### Placeholder Violations

**Issue:** Code contains TODO, FIXME, or PLACEHOLDER comments
```json
"remediation": {
    "placeholders": [
        "Remove TODO at src/core/module.py:15",
        "Remove FIXME at src/core/module.py:23"
    ]
}
```

### Coverage Failures

**Issue:** Test coverage below 95% threshold
```json
"remediation": {
    "coverage": [
        "Increase test coverage from 87% to 95%",
        "Add tests for uncovered lines 45-67 in src/core/module.py"
    ]
}
```

### Type Checking Failures

**Issue:** Missing or incorrect type hints
```json
"remediation": {
    "mypy": [
        "Add type hints to src/core/module.py",
        "Fix type error at src/core/module.py:34 - Incompatible return type"
    ]
}
```

### Context Gate Failures

**Issue:** Missing required context files
```json
"remediation": {
    "context_gate": [
        "Create required context file: context/hypothesis.md",
        "Add content to context/evidence.json",
        "Add at least 3 P1 priority sources to evidence.json"
    ]
}
```

## MEA State Tracking

The MEA cycle maintains state in `artifacts/mea_state.json`:

```json
{
    "session_id": "mea-20241024-154523-a1b2c3d4",
    "current_attempt": 2,
    "max_attempts": 3,
    "status": "in_progress",
    "attempts": [
        {
            "attempt_number": 1,
            "validation_status": "blocked",
            "gates": {
                "tdd_guard": "fail",
                "coverage": "pass",
                "placeholders": "fail"
            },
            "fixes_attempted": ["tdd_guard", "placeholders"]
        }
    ],
    "validation_gates": {
        "tdd_guard": [
            {"attempt": 1, "status": "fail"},
            {"attempt": 2, "status": "pass"}
        ]
    }
}
```

## Testing MEA Implementation

### Run Test Suite

```powershell
# Test simple passing case
.\commands\test-mea.ps1 -TestCase simple

# Test TDD violations
.\commands\test-mea.ps1 -TestCase tdd

# Test complex issues (placeholders, stubs)
.\commands\test-mea.ps1 -TestCase complex

# Run all tests
.\commands\test-mea.ps1 -TestCase all
```

## Advanced Usage

### Custom Fix Generation

The MEA system automatically generates fixes for common issues:

1. **TDD Fixes:**
   - Adds `@pytest.mark.cp` decorators
   - Adds basic Hypothesis property tests
   - Adds failure path tests with `pytest.raises`

2. **Placeholder Fixes:**
   - Removes TODO/FIXME/PLACEHOLDER comments
   - Cleans up extra blank lines

3. **Type Hint Fixes:**
   - Adds basic return type hints (-> None)
   - Suggests type annotations for parameters

4. **Context Fixes:**
   - Creates missing context files with templates
   - Adds required evidence.json structure
   - Generates basic hypothesis.md and design.md

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run MEA Validation
  run: |
    $code = Get-Content code-batch.json
    pwsh sca-protocol-skill/commands/mea-cycle.ps1 -CodeBatch $code -Attempt 1
```

## Troubleshooting

### Common Issues

1. **"Failed to import MEA modules"**
   - Ensure `sca/mea/` directory exists with all required modules
   - Check Python path includes skill directory

2. **"Invalid JSON in CodeBatch"**
   - Verify JSON is properly formatted
   - Use `ConvertTo-Json -Compress` for PowerShell objects

3. **"Maximum attempts reached"**
   - Review persistent failures in mea_state.json
   - Manual intervention may be required for complex issues

4. **"Task directory not found"**
   - Ensure you've created and selected a task
   - Run `.\commands\get-task.ps1` to verify current task

### Viewing MEA Reports

Generate a human-readable report from MEA state:

```python
from sca.mea.state_manager import MEAStateManager
manager = MEAStateManager("tasks/001-my-feature")
print(manager.export_report())
```

## Best Practices

1. **Start with Context:** Ensure context files are complete before coding
2. **Write Tests First:** Follow TDD - tests before implementation
3. **Use Property Tests:** Include Hypothesis tests for better coverage
4. **Clean Code:** Avoid placeholders and stub functions
5. **Type Everything:** Add comprehensive type hints
6. **Review State:** Check mea_state.json to understand failure patterns

## API Reference

### PowerShell Commands

```powershell
# Main MEA cycle
.\mea-cycle.ps1 -CodeBatch <json> -Attempt <1-3> [-MaxAttempts <3>]

# Test MEA
.\test-mea.ps1 -TestCase <simple|tdd|complex|all>
```

### Python API

```python
from sca.mea.orchestrator import MEAOrchestrator

# Initialize
orchestrator = MEAOrchestrator(task_dir="tasks/001-feature")

# Write code
orchestrator.write_code_batch({"src/file.py": "content"})

# Validate
result = orchestrator.execute_validation()

# Parse failures
failures = orchestrator.parse_failures(result)

# Apply fixes
fixed_files = orchestrator.apply_fixes(failures)

# Full cycle
mea_result = orchestrator.execute_mea_cycle(
    code_batch={"src/file.py": "content"},
    attempt=1,
    max_attempts=3
)
```

## Version History

- **v0.4.0** - Full MEA orchestration with auto-fix capabilities
- **v0.3.0** - Basic validation-only workflow
- **v0.2.0** - Task management features
- **v0.1.0** - Initial SCA protocol implementation
<#
.SYNOPSIS
    Test the MEA (Mandatory Execution Algorithm) implementation

.DESCRIPTION
    Provides test cases to verify the MEA cycle is working correctly.
    Tests both passing and failing scenarios.

.PARAMETER TestCase
    Which test case to run: "simple", "tdd", "complex", or "all"

.EXAMPLE
    .\test-mea.ps1 -TestCase simple
    .\test-mea.ps1 -TestCase all
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("simple", "tdd", "complex", "all")]
    [string]$TestCase = "simple"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== MEA Test Suite ===" -ForegroundColor Cyan
Write-Host "Testing MEA implementation with case: $TestCase" -ForegroundColor Yellow

# Test Case 1: Simple passing case
function Test-SimpleCase {
    Write-Host "`n[TEST] Simple Passing Case" -ForegroundColor Green

    $code = @{
        "src/core/calculator.py" = @"
"""Simple calculator module."""
from typing import Union


def add(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of x and y
    """
    return x + y


def subtract(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """Subtract y from x.

    Args:
        x: First number
        y: Number to subtract

    Returns:
        Difference of x and y
    """
    return x - y
"@

        "tests/test_calculator.py" = @"
"""Tests for calculator module."""
import pytest
from hypothesis import given
from hypothesis import strategies as st
from src.core.calculator import add, subtract


@pytest.mark.cp
@given(st.integers(), st.integers())
def test_add_property(x: int, y: int) -> None:
    """Property test for addition."""
    result = add(x, y)
    assert result == x + y
    assert add(y, x) == result  # Commutative


@pytest.mark.cp
def test_add_simple() -> None:
    """Simple test for addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


@pytest.mark.cp
def test_add_failure() -> None:
    """Test failure path for addition."""
    with pytest.raises(TypeError):
        add("not", "numbers")


@pytest.mark.cp
@given(st.integers(), st.integers())
def test_subtract_property(x: int, y: int) -> None:
    """Property test for subtraction."""
    result = subtract(x, y)
    assert result == x - y
    assert subtract(x, 0) == x


@pytest.mark.cp
def test_subtract_failure() -> None:
    """Test failure path for subtraction."""
    with pytest.raises(TypeError):
        subtract(None, 5)
"@
    } | ConvertTo-Json -Compress

    Write-Host "Running MEA cycle with simple valid code..." -ForegroundColor White
    & (Join-Path $PSScriptRoot "mea-cycle.ps1") -CodeBatch $code -Attempt 1
}

# Test Case 2: TDD violation case
function Test-TDDCase {
    Write-Host "`n[TEST] TDD Violation Case" -ForegroundColor Yellow

    $code = @{
        "src/core/processor.py" = @"
def process_data(data):
    # Missing type hints
    return data * 2
"@

        "tests/test_processor.py" = @"
# Missing @pytest.mark.cp and property tests
def test_process():
    from src.core.processor import process_data
    assert process_data(5) == 10
"@
    } | ConvertTo-Json -Compress

    Write-Host "Running MEA cycle with TDD violations..." -ForegroundColor White
    & (Join-Path $PSScriptRoot "mea-cycle.ps1") -CodeBatch $code -Attempt 1

    Write-Host "`nThis should have failed with TDD violations." -ForegroundColor Yellow
    Write-Host "You would normally fix the issues and run with -Attempt 2" -ForegroundColor Cyan
}

# Test Case 3: Complex case with placeholders
function Test-ComplexCase {
    Write-Host "`n[TEST] Complex Case with Placeholders" -ForegroundColor Magenta

    $code = @{
        "src/core/analyzer.py" = @"
"""Analyzer module with issues."""


def analyze(data: list) -> dict:
    """Analyze data.

    TODO: Implement actual analysis
    FIXME: Add error handling
    """
    # PLACEHOLDER: Real implementation needed
    return {"result": "stub"}
"@

        "tests/test_analyzer.py" = @"
"""Tests for analyzer - incomplete."""
from src.core.analyzer import analyze


def test_analyze():
    # Missing decorators and property tests
    result = analyze([1, 2, 3])
    assert result is not None
"@
    } | ConvertTo-Json -Compress

    Write-Host "Running MEA cycle with multiple issues..." -ForegroundColor White
    & (Join-Path $PSScriptRoot "mea-cycle.ps1") -CodeBatch $code -Attempt 1

    Write-Host "`nThis should have failed with multiple violations:" -ForegroundColor Yellow
    Write-Host "  - Placeholder comments (TODO, FIXME, PLACEHOLDER)" -ForegroundColor White
    Write-Host "  - Missing test decorators" -ForegroundColor White
    Write-Host "  - Missing property tests" -ForegroundColor White
    Write-Host "  - Stub function detected" -ForegroundColor White
}

# Run selected test case(s)
switch ($TestCase) {
    "simple" { Test-SimpleCase }
    "tdd" { Test-TDDCase }
    "complex" { Test-ComplexCase }
    "all" {
        Test-SimpleCase
        Start-Sleep -Seconds 2
        Test-TDDCase
        Start-Sleep -Seconds 2
        Test-ComplexCase
    }
}

Write-Host "`n=== MEA Test Complete ===" -ForegroundColor Cyan
Write-Host @"

Next steps to test MEA:
1. Create a new task: .\new-task.ps1 -TaskId 999 -TaskSlug mea-test
2. Run test cases: .\test-mea.ps1 -TestCase all
3. For failed tests, apply fixes and retry with -Attempt 2
4. Check artifacts/mea_state.json for state tracking

"@ -ForegroundColor White
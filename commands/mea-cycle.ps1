<#
.SYNOPSIS
    Execute MEA (Mandatory Execution Algorithm) cycle with auto-fix capability

.DESCRIPTION
    Implements the Write → Validate → Fix → Repeat loop for the SCA Protocol.
    Writes code files, validates them, and provides remediation guidance.

.PARAMETER CodeBatch
    JSON string containing files to write. Format: {"path/file.py": "content", ...}

.PARAMETER Attempt
    Current MEA attempt number (1-3). Default: 1

.PARAMETER MaxAttempts
    Maximum number of attempts before giving up. Default: 3

.EXAMPLE
    $code = @{"src/test.py" = "def test(): pass"} | ConvertTo-Json
    .\mea-cycle.ps1 -CodeBatch $code -Attempt 1

.NOTES
    This command implements the full MEA cycle as specified in protocol v13.8
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$CodeBatch,

    [Parameter(Mandatory=$false)]
    [int]$Attempt = 1,

    [Parameter(Mandatory=$false)]
    [int]$MaxAttempts = 3
)

$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Get task information
try {
    $taskInfo = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
    $taskDir = $taskInfo.TASK_DIR
    $repoRoot = $taskInfo.REPO_ROOT
} catch {
    Write-Error "Failed to get task information. Ensure you have a valid task selected."
    exit 1
}

# Get skill path
$skillPath = Get-SCASkillPath

# Validate attempt number
if ($Attempt -lt 1 -or $Attempt -gt $MaxAttempts) {
    Write-Error "Attempt must be between 1 and $MaxAttempts"
    exit 1
}

# Set environment variables for Python
$env:TASK_DIR = $taskDir
$env:TASK_ID = Split-Path -Leaf $taskDir | ForEach-Object { if ($_ -match '^(\d+)-') { $matches[1] } else { "999" } }
$env:TASK_SLUG = Split-Path -Leaf $taskDir | ForEach-Object { if ($_ -match '^\d+-(.+)$') { $matches[1] } else { "unknown" } }
$env:SCA_SKILL_PATH = $skillPath
$env:MEA_ATTEMPT = $Attempt
$env:MEA_MAX_ATTEMPTS = $MaxAttempts

# Change to repository root for execution
Push-Location $repoRoot

try {
    # Execute MEA cycle via Python
    $pythonScript = @'
import os, sys, json
import traceback

# Add skill path to Python path
skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)

try:
    from sca.mea.orchestrator import MEAOrchestrator

    # Initialize orchestrator
    orchestrator = MEAOrchestrator(
        task_dir=os.environ['TASK_DIR'],
        skill_path=skill_path
    )

    # Parse code batch
    code_batch_json = sys.argv[1] if len(sys.argv) > 1 else '{}'
    try:
        code_batch = json.loads(code_batch_json)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "agent": "SCA",
            "protocol_version": "13.8",
            "status": "error",
            "error": f"Invalid JSON in CodeBatch: {str(e)}"
        }, indent=2))
        sys.exit(1)

    # Execute MEA cycle
    result = orchestrator.execute_mea_cycle(
        code_batch=code_batch,
        attempt=int(os.environ['MEA_ATTEMPT']),
        max_attempts=int(os.environ['MEA_MAX_ATTEMPTS'])
    )

    # Output MEA result
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    sys.exit(0 if result.get('status') == 'ok' else 1)

except ImportError as e:
    print(json.dumps({
        "agent": "SCA",
        "protocol_version": "13.8",
        "status": "error",
        "error": f"Failed to import MEA modules: {str(e)}",
        "hint": "Ensure the MEA modules are properly installed in sca/mea/"
    }, indent=2))
    sys.exit(1)

except Exception as e:
    print(json.dumps({
        "agent": "SCA",
        "protocol_version": "13.8",
        "status": "error",
        "error": f"MEA cycle failed: {str(e)}",
        "traceback": traceback.format_exc()
    }, indent=2))
    sys.exit(1)
'@

    # Execute the Python script with the code batch as argument
    $result = $pythonScript | python - $CodeBatch

    # Parse the result to check status
    try {
        $meaResult = $result | ConvertFrom-Json

        # Provide user-friendly output based on status
        if ($meaResult.status -eq "ok") {
            Write-Host "`n[MEA] SUCCESS - All validation gates passed!" -ForegroundColor Green
            Write-Host "Ready to run snapshot-save.ps1" -ForegroundColor Cyan
        }
        elseif ($meaResult.status -eq "blocked" -and $Attempt -lt $MaxAttempts) {
            Write-Host "`n[MEA] BLOCKED - Validation failed on attempt $Attempt/$MaxAttempts" -ForegroundColor Yellow

            if ($meaResult.remediation) {
                Write-Host "`nRequired fixes:" -ForegroundColor Cyan
                foreach ($gate in $meaResult.remediation.PSObject.Properties) {
                    Write-Host "  $($gate.Name):" -ForegroundColor Yellow
                    foreach ($fix in $gate.Value) {
                        Write-Host "    - $fix" -ForegroundColor White
                    }
                }
            }

            Write-Host "`nNext step: Apply fixes and run with -Attempt $($Attempt + 1)" -ForegroundColor Cyan
        }
        else {
            Write-Host "`n[MEA] FAILED - Maximum attempts reached or critical error" -ForegroundColor Red
            Write-Host "Manual intervention required" -ForegroundColor Yellow
        }
    }
    catch {
        # If we can't parse the result, just output it as-is
        Write-Output $result
    }

} catch {
    Write-Error "MEA cycle execution failed: $_"
    exit 1
} finally {
    Pop-Location
}
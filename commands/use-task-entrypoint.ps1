#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Switch to a different task with session tracking and validation (Skill Entrypoint).

.DESCRIPTION
  Changes the current task in .sca/profile.json, runs workspace and context
  validation on the target task, and logs the operation to the session event stream.

.PARAMETER TaskId
  Task identifier to switch to (e.g., "001-initial-setup")

.NOTES
  - Invokes through skill system for session tracking
  - Updates .sca/profile.json current_task
  - Runs workspace + context validation gates on target task
  - Writes run_context.json, run_manifest.json, run_events.jsonl
#>

param(
  # Accept either a single key "<id>-<slug>" or separate parts
  [Parameter(Mandatory=$false)]
  [string]$Task,

  [Parameter(Mandatory=$false)]
  [string]$TaskId,

  [Parameter(Mandatory=$false)]
  [string]$TaskSlug
)

$ErrorActionPreference = "Stop"

# Import shared utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Get current state before switching
$beforeSwitch = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$oldTaskDir = $beforeSwitch.TASK_DIR
$repoRoot = $beforeSwitch.REPO_ROOT

# Initialize session tracker on OLD task before switching
$skillPath = Get-SCASkillPath
$env:SCA_SKILL_PATH = $skillPath

Push-Location $repoRoot

try {
    # Log the switch START on the old task's session
    $logSwitchStart = @"
import sys
import os
from pathlib import Path

skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)

from sca.session_tracker import get_or_create_tracker

old_task_dir = Path(r'$oldTaskDir')
if old_task_dir.exists():
    tracker = get_or_create_tracker(old_task_dir)
    tracker.log_event('task', 'switch-from', 'start', {'target': '$TaskId'})
"@

    python -c $logSwitchStart

    # Parse task key into id/slug for the switch
    if ($Task) {
        if ($Task -notmatch '-') { throw "Task must be in <id>-<slug> format (e.g., 001-initial-setup)" }
        $idx = $Task.IndexOf('-')
        $TaskId = $Task.Substring(0,$idx)
        $TaskSlug = $Task.Substring($idx+1)
    } elseif ($TaskId -and -not $TaskSlug) {
        if ($TaskId -match '-') {
            $parts = $TaskId.Split('-',2)
            $TaskId = $parts[0]
            $TaskSlug = $parts[1]
        } else {
            throw "TaskSlug is required when TaskId does not include '-'"
        }
    }

    # Now perform the actual switch
    $switchResult = & (Join-Path $PSScriptRoot "use-task.ps1") -TaskId $TaskId -TaskSlug $TaskSlug

    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
        Write-Error "Task switch failed"
        exit 1
    }

    # Get new task info after switching
    $j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
    $taskDir = $j.TASK_DIR
    $auto = $j.AUTO
    $safeMode = $j.SAFE_MODE
    $dryRun = $j.DRY_RUN

    # Run validation on the NEW task with session tracking
    $pythonScript = @"
import sys
import os
import json
from pathlib import Path

# Add skill to path
skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)

from sca.session_tracker import get_or_create_tracker
from sca.workspace_guard import TaskPaths
from sca.validator_chain import run_validators
from sca.output_contract import current_header_from_env

# Set environment for output contract
os.environ['phase'] = 'context'
os.environ['AUTO'] = '$auto'
os.environ['SAFE_MODE'] = '$safeMode'
os.environ['DRY_RUN'] = '$dryRun'
os.environ['TASK_DIR'] = r'$taskDir'

# Initialize session tracker on NEW task
task_dir = Path(r'$taskDir')
tracker = get_or_create_tracker(task_dir)
tracker.log_event('entrypoint', 'use-task', 'start', {'task_id': '$TaskId', 'switched_from': r'$oldTaskDir'})

# Extract task_id from path
task_id = task_dir.name

# Write run context
tracker.write_run_context(
    task_id=task_id,
    phase='switch',
    tools=['workspace_validator', 'context_validator'],
    cp_files=[],
    data_sources=[],
    config={'switched_from': r'$oldTaskDir'}
)

# Build task paths
tp = TaskPaths(task_dir=str(task_dir))

# Run validation gates (workspace + context)
validation_result = run_validators(
    tp,
    include_context=True,
    include_traceability=False,  # Not required for switch operations
    tracker=tracker
)

# Build response
hdr = current_header_from_env()
hdr['task_id'] = task_id
hdr['status'] = validation_result['status']
hdr['phase'] = 'switch'

# Add run info
hdr['run'] = tracker.get_run_info()

# Add validation results to gates using per-checks if available
if 'gates' not in hdr:
    hdr['gates'] = {}

_ok = validation_result.get('status', 'blocked') == 'ok'
_checks = validation_result.get('checks', {})
hdr['gates']['workspace'] = 'pass' if _checks.get('workspace', _ok) else 'fail'
hdr['gates']['context'] = 'pass' if _checks.get('context_gate', _ok) else 'fail'

# Add task metadata
task_info = {
    'task_dir': str(task_dir),
    'repo_root': r'$repoRoot',
    'task_id': '$TaskId',
    'switched_from': r'$oldTaskDir',
    'is_active': True
}

if validation_result['status'] != 'ok':
    hdr['failure'] = validation_result.get('failure', 'Validation failed')
    task_info['validation_failure'] = hdr['failure']

hdr['task_info'] = task_info

# Write run manifest
tracker.write_run_manifest()

# Log completion
if validation_result['status'] == 'ok':
    tracker.log_event('entrypoint', 'use-task', 'complete', {'task_id': '$TaskId'})
else:
    tracker.log_event('entrypoint', 'use-task', 'fail', {
        'task_id': '$TaskId',
        'failure': hdr.get('failure', '')
    })

# Output JSON
print(json.dumps(hdr, indent=2))
"@

    python -c $pythonScript

} finally {
    Pop-Location
}

#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Create new task with session tracking and validation (Skill Entrypoint).

.DESCRIPTION
  Creates a new task directory structure, runs workspace and context validation,
  and logs the operation to the session event stream. This is the skill
  entrypoint version that provides full protocol compliance.

.PARAMETER TaskId
  Task identifier in format: <number>-<slug> (e.g., "001-initial-setup")

.PARAMETER Description
  Brief description of the task purpose

.NOTES
  - Invokes through skill system for session tracking
  - Creates task structure and .sca profile if needed
  - Runs workspace + context validation gates
  - Writes run_context.json, run_manifest.json, run_events.jsonl
#>

param(
  # Accept either a single key "<id>-<slug>" or separate parts
  [Parameter(Mandatory=$false)]
  [string]$Task,

  [Parameter(Mandatory=$false)]
  [string]$TaskId,

  [Parameter(Mandatory=$false)]
  [string]$TaskSlug,

  [Parameter(Mandatory=$false)]
  [string]$Description = ""
)

$ErrorActionPreference = "Stop"

# Import shared utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Get current repo info
$currentDir = (Get-Location).Path
$skillPath = Get-SCASkillPath
$env:SCA_SKILL_PATH = $skillPath

# Parse task key into id/slug
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

# Create the task using existing logic (requires TaskId and TaskSlug)
$createResult = & (Join-Path $PSScriptRoot "new-task.ps1") -TaskId $TaskId -TaskSlug $TaskSlug -Description $Description

if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
    Write-Error "Task creation failed"
    exit 1
}

# Discover the newly created task
$j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$taskDir = $j.TASK_DIR
$repoRoot = $j.REPO_ROOT
$auto = $j.AUTO
$safeMode = $j.SAFE_MODE
$dryRun = $j.DRY_RUN

# Change to repo root for validation
Push-Location $repoRoot

try {
    # Run Python validation with session tracking
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

# Initialize session tracker
task_dir = Path(r'$taskDir')
tracker = get_or_create_tracker(task_dir)
tracker.log_event('entrypoint', 'new-task', 'start', {'task_id': '$TaskId', 'description': '$Description'})

# Extract task_id from path
task_id = task_dir.name

# Write run context
tracker.write_run_context(
    task_id=task_id,
    phase='creation',
    tools=['workspace_validator', 'context_validator'],
    cp_files=[],
    data_sources=[],
    config={'description': '$Description'}
)

# Build task paths
tp = TaskPaths(task_dir=str(task_dir))

# Run validation gates (workspace + context)
# Note: Newly created tasks will likely fail context gate until user adds hypothesis, design, etc.
validation_result = run_validators(
    tp,
    include_context=True,
    include_traceability=False,  # Not required for creation
    tracker=tracker
)

# Build response
hdr = current_header_from_env()
hdr['task_id'] = task_id
hdr['status'] = validation_result['status']
hdr['phase'] = 'creation'

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
    'description': '$Description',
    'created': True
}

if validation_result['status'] != 'ok':
    hdr['failure'] = validation_result.get('failure', 'Validation failed')
    task_info['validation_failure'] = hdr['failure']
    task_info['next_steps'] = [
        'Populate context/hypothesis.md with metrics, Critical Path, and thresholds',
        'Populate context/design.md with data strategy and verification plan',
        'Add >=3 P1 sources to context/evidence.json',
        'Create context/data_sources.json with source metadata',
        'Add context/adr.md and context/assumptions.md'
    ]

hdr['task_info'] = task_info

# Write run manifest
tracker.write_run_manifest()

# Log completion
if validation_result['status'] == 'ok':
    tracker.log_event('entrypoint', 'new-task', 'complete', {'task_id': '$TaskId'})
else:
    tracker.log_event('entrypoint', 'new-task', 'partial', {
        'task_id': '$TaskId',
        'note': 'Task created but context validation failed (expected for new tasks)'
    })

# Output JSON
print(json.dumps(hdr, indent=2))
"@

    python -c $pythonScript

} finally {
    Pop-Location
}

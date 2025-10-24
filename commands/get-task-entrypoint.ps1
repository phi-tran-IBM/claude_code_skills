#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Get current task with session tracking and validation (Skill Entrypoint).

.DESCRIPTION
  Discovers the current task, runs workspace and context validation gates,
  and logs the operation to the session event stream. This is the skill
  entrypoint version that provides full protocol compliance.

.NOTES
  - Invokes through skill system for session tracking
  - Runs workspace + context validation gates
  - Writes run_context.json, run_manifest.json, run_events.jsonl
  - Returns JSON with task info + validation status
#>

param()

$ErrorActionPreference = "Stop"

# Import shared utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Discover repository and task
$j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$taskDir = $j.TASK_DIR
$repoRoot = $j.REPO_ROOT
$auto = $j.AUTO
$safeMode = $j.SAFE_MODE
$dryRun = $j.DRY_RUN

# Get skill path
$skillPath = Get-SCASkillPath
$env:SCA_SKILL_PATH = $skillPath

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
tracker.log_event('entrypoint', 'get-task', 'start')

# Extract task_id from path
task_id = task_dir.name

# Write run context
tracker.write_run_context(
    task_id=task_id,
    phase='query',
    tools=['workspace_validator', 'context_validator'],
    cp_files=[],
    data_sources=[],
    config={}
)

# Build task paths
tp = TaskPaths(task_dir=str(task_dir))

# Run validation gates (workspace + context)
validation_result = run_validators(
    tp,
    include_context=True,
    include_traceability=False,  # Not required for query operations
    tracker=tracker
)

# Build response
hdr = current_header_from_env()
hdr['task_id'] = task_id
hdr['status'] = validation_result['status']
hdr['phase'] = 'query'

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
    'auto': '$auto',
    'safe_mode': '$safeMode',
    'dry_run': '$dryRun'
}

if validation_result['status'] != 'ok':
    hdr['failure'] = validation_result.get('failure', 'Validation failed')
    task_info['validation_failure'] = hdr['failure']

hdr['task_info'] = task_info

# Write run manifest
tracker.write_run_manifest()

# Log completion
if validation_result['status'] == 'ok':
    tracker.log_event('entrypoint', 'get-task', 'complete')
else:
    tracker.log_event('entrypoint', 'get-task', 'fail', {'failure': hdr.get('failure', '')})

# Output JSON
print(json.dumps(hdr, indent=2))
"@

    python -c $pythonScript

} finally {
    Pop-Location
}

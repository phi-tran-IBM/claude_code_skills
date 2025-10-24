#!/usr/bin/env pwsh
<#
.SYNOPSIS
  List all tasks in current directory with session tracking (Skill Entrypoint).

.DESCRIPTION
  Enumerates all tasks in the ./tasks/ directory of the current working directory,
  retrieves metadata and validation status for each, and logs the operation to
  the session event stream.

.NOTES
  - Invokes through skill system for session tracking
  - Lists tasks from current directory only (not discovered parent)
  - Runs workspace validation on current directory
  - Writes run_context.json, run_manifest.json, run_events.jsonl
  - Returns JSON array of tasks with metadata
#>

param()

$ErrorActionPreference = "Stop"

# Import shared utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Use CURRENT directory (not discovered parent) per user requirement
$currentDir = (Get-Location).Path
$tasksDir = Join-Path $currentDir "tasks"

# Get skill path
$skillPath = Get-SCASkillPath
$env:SCA_SKILL_PATH = $skillPath

# Check if tasks directory exists
if (-not (Test-Path $tasksDir)) {
    # No tasks directory - return empty list with session tracking if current task exists
    $j = & (Join-Path $PSScriptRoot "get-task.ps1") -ErrorAction SilentlyContinue | ConvertFrom-Json

    if ($null -eq $j) {
        # No current task, no tasks directory - just return empty
        $emptyResult = @{
            tasks = @()
            current_dir = $currentDir
            tasks_dir = $tasksDir
            exists = $false
        }
        Write-Output ($emptyResult | ConvertTo-Json -Depth 10)
        exit 0
    }

    # We have a current task (from parent) but no local tasks directory
    $taskDir = $j.TASK_DIR
    Push-Location (Split-Path $taskDir -Parent)

    try {
        $pythonScript = @"
import sys
import os
import json
from pathlib import Path

skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)

from sca.session_tracker import get_or_create_tracker

task_dir = Path(r'$taskDir')
tracker = get_or_create_tracker(task_dir)
tracker.log_event('entrypoint', 'list-tasks', 'complete', {
    'current_dir': r'$currentDir',
    'tasks_found': 0,
    'note': 'No local tasks directory'
})

result = {
    'tasks': [],
    'current_dir': r'$currentDir',
    'tasks_dir': r'$tasksDir',
    'exists': False,
    'run': tracker.get_run_info()
}

print(json.dumps(result, indent=2))
"@
        python -c $pythonScript
    } finally {
        Pop-Location
    }
    exit 0
}

# Get current task for session tracking
$j = & (Join-Path $PSScriptRoot "get-task.ps1") -ErrorAction SilentlyContinue | ConvertFrom-Json

# Enumerate task directories
$taskFolders = Get-ChildItem -Path $tasksDir -Directory | Where-Object { $_.Name -match '^\d+-' }

# Build task info array
$taskList = @()
foreach ($folder in $taskFolders) {
    $taskId = $folder.Name
    $taskPath = $folder.FullName

    # Check if this is the current task
    $isCurrent = ($null -ne $j -and $j.TASK_DIR -eq $taskPath)

    # Read metadata if available
    $stateFile = Join-Path $taskPath "artifacts\state.json"
    $lastPhase = "unknown"
    $lastStatus = "unknown"
    $lastRun = $null

    if (Test-Path $stateFile) {
        try {
            $state = Get-Content $stateFile -Raw | ConvertFrom-Json
            $lastPhase = $state.phase
            $lastStatus = $state.status
        } catch {
            # Ignore parse errors
        }
    }

    # Check for session tracking
    $sessionFile = Join-Path $taskPath "artifacts\session_id.txt"
    $sessionId = $null
    if (Test-Path $sessionFile) {
        $sessionId = (Get-Content $sessionFile -Raw).Trim()
    }

    # Check for last run
    $eventsFile = Join-Path $taskPath "artifacts\run_events.jsonl"
    if (Test-Path $eventsFile) {
        $events = Get-Content $eventsFile
        if ($events.Count -gt 0) {
            $lastEvent = $events[-1] | ConvertFrom-Json
            $lastRun = $lastEvent.run_id
        }
    }

    $taskList += @{
        task_id = $taskId
        task_dir = $taskPath
        is_current = $isCurrent
        last_phase = $lastPhase
        last_status = $lastStatus
        session_id = $sessionId
        last_run_id = $lastRun
    }
}

# Run session tracking and workspace validation
Push-Location $currentDir

try {
    # Write task list to temp file for Python to read
    $tempFile = [System.IO.Path]::GetTempFileName()
    $taskList | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8

    # Determine which task to track under (current task if exists, otherwise no tracking)
    if ($null -ne $j) {
        $trackingTaskDir = $j.TASK_DIR
        $trackingEnabled = "True"
    } else {
        $trackingTaskDir = ""
        $trackingEnabled = "False"
    }

    $pythonScript = @"
import sys
import os
import json
from pathlib import Path

skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)

from sca.session_tracker import get_or_create_tracker
from sca.workspace_guard import TaskPaths
from sca.validator_chain import run_validators

tracking_enabled = $trackingEnabled == 'True'

# Read task list from temp file (utf-8-sig to handle BOM)
with open(r'$tempFile', 'r', encoding='utf-8-sig') as f:
    task_list = json.load(f)

result = {
    'tasks': task_list,
    'current_dir': r'$currentDir',
    'tasks_dir': r'$tasksDir',
    'exists': True,
    'task_count': len(task_list)
}

if tracking_enabled:
    task_dir = Path(r'$trackingTaskDir')
    tracker = get_or_create_tracker(task_dir)
    tracker.log_event('entrypoint', 'list-tasks', 'start', {'current_dir': r'$currentDir'})

    # Write run context
    tracker.write_run_context(
        task_id=task_dir.name,
        phase='query',
        tools=['workspace_validator'],
        cp_files=[],
        data_sources=[],
        config={'operation': 'list-tasks', 'current_dir': r'$currentDir'}
    )

    # Run workspace validation on current directory
    # Build minimal task paths for workspace check
    current_path = Path(r'$currentDir')
    tp = TaskPaths(task_dir=str(current_path))

    validation_result = run_validators(
        tp,
        include_context=False,
        include_traceability=False,
        tracker=tracker
    )

    # Map workspace_valid using per-check if available (current directory)
    _ok = (validation_result.get('status', 'blocked') == 'ok')
    _checks = validation_result.get('checks', {})
    result['workspace_valid'] = bool(_checks.get('workspace', _ok))

    # Write run manifest
    tracker.write_run_manifest()

    tracker.log_event('entrypoint', 'list-tasks', 'complete', {
        'current_dir': r'$currentDir',
        'tasks_found': len(task_list)
    })

    result['run'] = tracker.get_run_info()

print(json.dumps(result, indent=2))
"@

    python -c $pythonScript

    # Clean up temp file
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }

} finally {
    Pop-Location
}

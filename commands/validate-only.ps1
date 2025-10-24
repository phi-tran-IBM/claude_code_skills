$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Discover current task & derive repo root from TASK_DIR
$j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$taskDir = $j.TASK_DIR
# Derive repo root from TASK_DIR (tasks dir is 2 levels up from task dir)
# TASK_DIR format: <PROJECT_ROOT>/tasks/<task-id-slug>
# So: PROJECT_ROOT = dirname(dirname(TASK_DIR))
$repoRoot = Split-Path (Split-Path $taskDir -Parent) -Parent

# Get skill path (fixed location)
$skillPath = Get-SCASkillPath

# Extract TASK_ID and TASK_SLUG from task directory name
# Expected format: tasks/<id>-<slug>
$taskDirName = Split-Path -Leaf $taskDir
if ($taskDirName -match '^(\d+)-(.+)$') {
    $taskId = $matches[1]
    $taskSlug = $matches[2]
} else {
    # Fallback: try to read from profile
    $profilePath = Join-Path $repoRoot ".sca\profile.json"
    if (Test-Path $profilePath) {
        try {
            $profile = Get-Content $profilePath | ConvertFrom-Json
            $taskId = $profile.current_task.task_id
            $taskSlug = $profile.current_task.task_slug
        } catch {
            $taskId = "999-unset"
            $taskSlug = "unset"
        }
    } else {
        $taskId = "999-unset"
        $taskSlug = "unset"
    }
}

# Intentionally avoid any stdout before JSON; keep metadata in logs only

# Set environment variables for Python
$env:TASK_DIR = $taskDir
$env:TASK_ID = $taskId
$env:TASK_SLUG = $taskSlug
$env:SCA_SKILL_PATH = $skillPath

# Change to the discovered repository root
Push-Location $repoRoot

try {
    $pythonScript = @'
import os, sys, json
skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)
from sca.validator_chain import run_validators
from sca.workspace_guard import TaskPaths
from sca.session_tracker import get_or_create_tracker

task_dir = os.environ["TASK_DIR"]
tp = TaskPaths(task_dir)
tracker = get_or_create_tracker(task_dir)

tracker.log_event("entrypoint", "validate-only", "start")

# Write run context
tracker.write_run_context(
    task_id=os.environ.get("TASK_ID", "unknown"),
    phase="validation",
    tools=["pytest", "mypy", "lizard", "interrogate", "bandit", "detect-secrets", "pip-audit"]
)

result = run_validators(
    task_paths=tp,
    include_context=True,
    include_cp=True,
    include_qa=True,
    include_memory=True,
    include_traceability=True,  # Always check traceability per protocol
    tracker=tracker
)

# Write manifest
tracker.write_run_manifest()

tracker.log_event("entrypoint", "validate-only", "complete" if result["status"] == "ok" else "fail", result)

# Print result with run info
result["run"] = tracker.get_run_info()
print(json.dumps(result))
'@

    $pythonScript | python -
} finally {
    Pop-Location
}

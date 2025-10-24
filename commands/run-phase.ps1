param(
  [string]$Phase = "auto",
  [string]$AUTO, [string]$SAFE_MODE, [string]$DRY_RUN
)
$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Discover current task & repo root
$j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$taskDir = $j.TASK_DIR
$repoRoot = $j.REPO_ROOT
if (-not $AUTO) { $AUTO=$j.AUTO }
if (-not $SAFE_MODE) { $SAFE_MODE=$j.SAFE_MODE }
if (-not $DRY_RUN) { $DRY_RUN=$j.DRY_RUN }

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
$env:AUTO = $AUTO
$env:SAFE_MODE = $SAFE_MODE
$env:DRY_RUN = $DRY_RUN
$env:SCA_SKILL_PATH = $skillPath

# Change to the discovered repository root
Push-Location $repoRoot

try {
    $pythonScript = @'
import os, sys
skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)
from sca.runner_wrapper import run
run(task_dir=os.environ["TASK_DIR"], phase=sys.argv[1],
    auto=os.environ["AUTO"], safe_mode=os.environ["SAFE_MODE"], dry_run=os.environ["DRY_RUN"])
'@

    $pythonScript | python - $Phase
} finally {
    Pop-Location
}

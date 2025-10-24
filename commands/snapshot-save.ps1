$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Discover current task & repo root
$j = & (Join-Path $PSScriptRoot "get-task.ps1") | ConvertFrom-Json
$taskDir = $j.TASK_DIR
$repoRoot = $j.REPO_ROOT

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
import os, sys
skill_path = os.environ.get('SCA_SKILL_PATH', 'sca-protocol-skill')
sys.path.insert(0, skill_path)
from sca.snapshot_manager import SnapshotManager
from sca.output_contract import current_header_from_env, print_header
from sca.session_tracker import get_or_create_tracker

task_dir = os.environ["TASK_DIR"]
tracker = get_or_create_tracker(task_dir)

tracker.log_event("entrypoint", "snapshot-save", "start")

# Write run context
tracker.write_run_context(
    task_id=os.environ.get("TASK_ID", "unknown"),
    phase="snapshot",
    tools=[]
)

sm = SnapshotManager(task_dir)
hdr = current_header_from_env()
hdr["run"] = tracker.get_run_info()

sm.snapshot_save(hdr, phase_hint=hdr.get("phase","unknown"))

# Write manifest
tracker.write_run_manifest()

tracker.log_event("entrypoint", "snapshot-save", "complete")

print_header(hdr, notes=["Snapshot forced"], self_checks=["snapshot ok"], next_actions=[])
'@

    $pythonScript | python -
} finally {
    Pop-Location
}

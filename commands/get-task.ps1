$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# Discover repository root (walks up to find .sca or tasks/)
$repo = Find-RepoRoot
$profile = Join-Path $repo ".sca\profile.json"

function Newest-Task([string]$root) {
  if (-not (Test-Path $root)) { return $null }
  $tasks = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue
  if (-not $tasks) { return $null }
  $tasks | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

if ($env:TASK_DIR) {
  $dir = $env:TASK_DIR; $auto = $env:AUTO; $safe = $env:SAFE_MODE; $dry=$env:DRY_RUN
} elseif (Test-Path $profile) {
  $j = Get-Content $profile | ConvertFrom-Json
  # Handle both old format (string) and new format (object)
  if ($j.current_task -is [string]) {
    $dir = Join-Path $repo "tasks\$($j.current_task)"
  } else {
    $dir = $j.current_task.task_dir
  }
  # Handle missing defaults (old format)
  if ($j.defaults) {
    $auto = $j.defaults.AUTO; $safe = $j.defaults.SAFE_MODE; $dry=$j.defaults.DRY_RUN
  } else {
    $auto = "2"; $safe = "on"; $dry = "off"
  }
} else {
  $candidate = Newest-Task (Join-Path $repo "tasks")
  if (-not $candidate) { throw "No tasks found and no profile set. Run commands\new-task.ps1 first." }
  $dir = $candidate.FullName; $auto="2"; $safe="on"; $dry="off"
}

[PSCustomObject]@{ TASK_DIR=$dir; AUTO=$auto; SAFE_MODE=$safe; DRY_RUN=$dry; REPO_ROOT=$repo } | ConvertTo-Json

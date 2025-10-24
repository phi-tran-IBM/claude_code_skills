param(
  [Parameter(Mandatory=$true)][string]$TaskId,
  [Parameter(Mandatory=$true)][string]$TaskSlug
)
$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# For use-task, look for tasks in current directory first, then walk up
$currentDir = (Get-Location).Path
$localTasksDir = Join-Path $currentDir "tasks"
$taskDirName = "{0}-{1}" -f $TaskId,$TaskSlug
$taskDir = Join-Path $localTasksDir $taskDirName

# If task not found locally, try discovered repo root
if (-not (Test-Path $taskDir)) {
    $repo = Find-RepoRoot
    $taskDir = Join-Path (Join-Path $repo "tasks") $taskDirName
} else {
    $repo = $currentDir
}

$profileDir = Join-Path $repo ".sca"
$profile = Join-Path $profileDir "profile.json"

if (-not (Test-Path $taskDir)) { throw "Task directory not found: $taskDir" }

# Determine if we should create/update a profile
$localProfileExists = Test-Path $profile
$parentHasProfile = -not (Should-CreateSCAProfile -StartPath $repo)
$defaults = @{ AUTO="2"; SAFE_MODE="on"; DRY_RUN="off" }

# If local profile exists, update it
if ($localProfileExists) {
  try {
    $j = Get-Content $profile | ConvertFrom-Json
    if ($j.defaults) { $defaults = $j.defaults }
  } catch {
    Write-Warning "Could not read existing profile, using default settings"
  }

  $prof = @{
    current_task = @{
      task_id  = $TaskId
      task_slug= $TaskSlug
      task_dir = (Resolve-Path $taskDir).Path
    }
    defaults = $defaults
  }
  $prof | ConvertTo-Json -Depth 5 | Out-File $profile -Encoding utf8
  Write-Host "Selected $($prof.current_task.task_dir)"
} elseif (-not $parentHasProfile) {
  # No profile anywhere, create new one
  New-Item -ItemType Directory -Force $profileDir | Out-Null
  $prof = @{
    current_task = @{
      task_id  = $TaskId
      task_slug= $TaskSlug
      task_dir = (Resolve-Path $taskDir).Path
    }
    defaults = $defaults
  }
  $prof | ConvertTo-Json -Depth 5 | Out-File $profile -Encoding utf8
  Write-Host "Created .sca/profile.json and selected $($prof.current_task.task_dir)"
} else {
  # Parent has profile, update it
  $parentProfile = Find-RepoRoot
  $parentProfilePath = Join-Path $parentProfile ".sca\profile.json"

  if (Test-Path $parentProfilePath) {
    try {
      $j = Get-Content $parentProfilePath | ConvertFrom-Json
      if ($j.defaults) { $defaults = $j.defaults }
    } catch {
      Write-Warning "Could not read parent profile"
    }

    $prof = @{
      current_task = @{
        task_id  = $TaskId
        task_slug= $TaskSlug
        task_dir = (Resolve-Path $taskDir).Path
      }
      defaults = $defaults
    }
    $prof | ConvertTo-Json -Depth 5 | Out-File $parentProfilePath -Encoding utf8
    Write-Host "Selected task: $((Resolve-Path $taskDir).Path)"
    Write-Host "Updated parent .sca/profile.json at: $parentProfile"
  } else {
    Write-Host "Selected task: $((Resolve-Path $taskDir).Path)"
    Write-Host "Warning: Could not find parent .sca/profile.json to update"
  }
}

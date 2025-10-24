param(
  [Parameter(Mandatory=$true)][string]$TaskId,
  [Parameter(Mandatory=$true)][string]$TaskSlug,
  [string]$Auto="2",
  [string]$Safe="on",
  [string]$Dry="off",
  [string]$Description=""
)
$ErrorActionPreference = "Stop"

# Import repository discovery utilities
. (Join-Path $PSScriptRoot "repo-utils.ps1")

# For new-task, always create tasks/ in the CURRENT directory (not discovered root)
# This allows nested projects to have their own local tasks
$repo = (Get-Location).Path
$profileDir = Join-Path $repo ".sca"
$profile = Join-Path $profileDir "profile.json"
$tasksDir = Join-Path $repo "tasks"
$taskDir = Join-Path $tasksDir ("{0}-{1}" -f $TaskId,$TaskSlug)

# Always create tasks directory and subdirectories
New-Item -ItemType Directory -Force $taskDir | Out-Null
"context","artifacts","qa","reports" | ForEach-Object { New-Item -ItemType Directory -Force (Join-Path $taskDir $_) | Out-Null }

# Copy templates from the skill folder
$skillPath = Get-SCASkillPath
$tpl = Join-Path $skillPath "templates\context"
if (Test-Path $tpl) {
    Copy-Item "$tpl\*" -Destination (Join-Path $taskDir "context") -Force -Recurse
} else {
    Write-Warning "Template directory not found at: $tpl"
}

# Determine if we should create a .sca/profile.json locally
# Check if one exists in current directory OR if parent has one (don't duplicate)
$localProfileExists = Test-Path $profile
$parentHasProfile = -not (Should-CreateSCAProfile -StartPath $repo)

if ($localProfileExists) {
    # Update existing local profile
    $j = Get-Content $profile | ConvertFrom-Json
    # Rebuild profile with updated current_task
    $prof = @{
      current_task = @{
        task_id  = $TaskId
        task_slug= $TaskSlug
        task_dir = (Resolve-Path $taskDir).Path
      }
    }
    # Preserve existing defaults if they exist, otherwise use provided values
    if ($j.defaults) {
        $prof.defaults = $j.defaults
    } else {
        $prof.defaults = @{ AUTO=$Auto; SAFE_MODE=$Safe; DRY_RUN=$Dry }
    }
    # Preserve other fields if they exist
    if ($j.project_name) { $prof.project_name = $j.project_name }
    if ($j.description) { $prof.description = $j.description }
    if ($j.created) { $prof.created = $j.created }
    if ($j.sca_version) { $prof.sca_version = $j.sca_version }

    $prof | ConvertTo-Json -Depth 5 | Out-File $profile -Encoding utf8
    Write-Host "Updated local .sca/profile.json at: $repo"
} elseif (-not $parentHasProfile) {
    # No profile exists anywhere, create new one locally
    New-Item -ItemType Directory -Force $profileDir | Out-Null
    $prof = @{
      current_task = @{
        task_id  = $TaskId
        task_slug= $TaskSlug
        task_dir = (Resolve-Path $taskDir).Path
      }
      defaults = @{ AUTO=$Auto; SAFE_MODE=$Safe; DRY_RUN=$Dry }
    }
    $prof | ConvertTo-Json -Depth 5 | Out-File $profile -Encoding utf8
    Write-Host "Created new .sca/profile.json at: $repo"
} else {
    # Parent has a profile, don't create duplicate
    Write-Host "Using parent .sca/profile.json (not creating duplicate)"
    Write-Host "To switch to this task, run: use-task.ps1 -TaskId $TaskId -TaskSlug $TaskSlug"
}

Write-Host "Created task at: $((Resolve-Path $taskDir).Path)"

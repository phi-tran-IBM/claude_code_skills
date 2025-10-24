# repo-utils.ps1
# Shared repository discovery and path resolution utilities for SCA Protocol Skill

<#
.SYNOPSIS
    Find the repository root by walking up the directory tree.

.DESCRIPTION
    Searches for .sca/profile.json OR tasks/ directory starting from current directory.
    PREFERENCE ORDER (highest to lowest):
    1. Directory with BOTH .sca/profile.json AND tasks/ (project root)
    2. Directory with .sca/profile.json (closest profile wins)
    3. Directory with tasks/ directory
    4. Current directory (fallback)

    This ensures project-level .sca takes precedence over workspace-level .sca,
    solving parallel task conflicts.

.OUTPUTS
    String - The resolved repository root path
#>
function Find-RepoRoot {
    [CmdletBinding()]
    param()

    $current = (Get-Location).Path
    $original = $current
    $maxDepth = 10  # Prevent infinite loops
    $depth = 0

    # Track candidates
    $candidateWithBoth = $null
    $candidateWithSCA = $null
    $candidateWithTasks = $null

    # Single pass: collect all candidates
    while ($current -and $depth -lt $maxDepth) {
        $scaProfile = Join-Path $current ".sca\profile.json"
        $tasksDir = Join-Path $current "tasks"

        $hasSCA = Test-Path $scaProfile
        $hasTasks = Test-Path $tasksDir -PathType Container

        # Priority 1: Directory with BOTH .sca and tasks/
        if ($hasSCA -and $hasTasks -and -not $candidateWithBoth) {
            $candidateWithBoth = $current
            Write-Verbose "Found BOTH .sca/profile.json AND tasks/ at: $current (HIGHEST PRIORITY)"
            # Return immediately - this is the best match
            return $current
        }

        # Priority 2: Directory with .sca only (closest wins)
        if ($hasSCA -and -not $candidateWithSCA) {
            $candidateWithSCA = $current
            Write-Verbose "Found .sca/profile.json at: $current"
        }

        # Priority 3: Directory with tasks/ only (closest wins)
        if ($hasTasks -and -not $candidateWithTasks) {
            $candidateWithTasks = $current
            Write-Verbose "Found tasks/ directory at: $current"
        }

        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or -not $parent) {
            break  # Reached filesystem root
        }
        $current = $parent
        $depth++
    }

    # Return best candidate found
    if ($candidateWithBoth) {
        Write-Verbose "Selected repo root (both .sca + tasks): $candidateWithBoth"
        return $candidateWithBoth
    }
    elseif ($candidateWithSCA) {
        Write-Verbose "Selected repo root (.sca only): $candidateWithSCA"
        return $candidateWithSCA
    }
    elseif ($candidateWithTasks) {
        Write-Verbose "Selected repo root (tasks only): $candidateWithTasks"
        return $candidateWithTasks
    }
    else {
        Write-Verbose "No .sca or tasks/ found, using current directory: $original"
        return $original
    }
}

<#
.SYNOPSIS
    Get the fixed path to the SCA protocol skill directory.

.OUTPUTS
    String - The hardcoded skill path
#>
function Get-SCASkillPath {
    [CmdletBinding()]
    param()

    return "C:\projects\Work Projects\sca-protocol-skill"
}

<#
.SYNOPSIS
    Check if a .sca/profile.json exists in current directory or any parent.

.OUTPUTS
    Boolean - $true if .sca/profile.json should be created, $false if one already exists
#>
function Should-CreateSCAProfile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)]
        [string]$StartPath = (Get-Location).Path
    )

    $current = $StartPath
    $maxDepth = 10
    $depth = 0

    while ($current -and $depth -lt $maxDepth) {
        $scaProfile = Join-Path $current ".sca\profile.json"
        if (Test-Path $scaProfile) {
            Write-Verbose ".sca/profile.json already exists at: $current"
            return $false
        }

        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or -not $parent) {
            break
        }
        $current = $parent
        $depth++
    }

    Write-Verbose "No .sca/profile.json found in hierarchy, should create one"
    return $true
}

<#
.SYNOPSIS
    Get information about the current repository and SCA configuration.

.OUTPUTS
    PSCustomObject with RepoRoot, SCAProfile, TasksDir, SkillPath
#>
function Get-SCARepoInfo {
    [CmdletBinding()]
    param()

    $repoRoot = Find-RepoRoot
    $scaProfile = Join-Path $repoRoot ".sca\profile.json"
    $tasksDir = Join-Path $repoRoot "tasks"
    $skillPath = Get-SCASkillPath

    return [PSCustomObject]@{
        RepoRoot = $repoRoot
        SCAProfile = $scaProfile
        TasksDir = $tasksDir
        SkillPath = $skillPath
        HasSCAProfile = (Test-Path $scaProfile)
        HasTasksDir = (Test-Path $tasksDir)
    }
}

# Functions are available when dot-sourced
# No Export-ModuleMember needed for dot-sourcing

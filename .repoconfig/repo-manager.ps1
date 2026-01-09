# Repo Manager - Cross-platform repository synchronization tool (PowerShell)
# Usage: .\repo-manager.ps1 <command> [args]

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    
    [Parameter(Position = 1)]
    [string]$Arg1,
    
    [Parameter(Position = 2)]
    [string]$Arg2
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigFile = Join-Path $ScriptDir "repos.json"

# Detect OS
function Get-OSType {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        return "windows"
    } elseif ($IsMacOS) {
        return "darwin"
    } else {
        return "linux"
    }
}

$OS = Get-OSType

# Initialize config if needed
function Initialize-Config {
    if (-not (Test-Path $ConfigFile)) {
        $config = @{
            version = 1
            description = "Tracked repositories for cross-machine sync"
            defaultBasePaths = @{
                linux = "/workspace"
                darwin = "/workspace"
                windows = "C:\dev"
            }
            repos = @()
        }
        $config | ConvertTo-Json -Depth 10 | Set-Content $ConfigFile -Encoding UTF8
        Write-Host "Initialized config at $ConfigFile" -ForegroundColor Green
    }
}

# Read config
function Get-Config {
    Get-Content $ConfigFile -Raw | ConvertFrom-Json
}

# Save config
function Save-Config {
    param([object]$Config)
    $Config | ConvertTo-Json -Depth 10 | Set-Content $ConfigFile -Encoding UTF8
}

# Get base path for current OS
function Get-BasePath {
    $config = Get-Config
    return $config.defaultBasePaths.$OS
}

# Add a repo to tracking
function Add-Repo {
    param([string]$RepoPath)
    
    if ([string]::IsNullOrEmpty($RepoPath)) {
        Write-Host "Error: Please provide a repository path" -ForegroundColor Red
        Write-Host "Usage: repo-manager.ps1 add <path>"
        return
    }

    # Resolve to absolute path
    if (-not (Test-Path $RepoPath)) {
        Write-Host "Error: Directory does not exist: $RepoPath" -ForegroundColor Red
        return
    }
    $RepoPath = (Resolve-Path $RepoPath).Path

    # Check if it's a git repo
    $gitDir = Join-Path $RepoPath ".git"
    if (-not (Test-Path $gitDir)) {
        Write-Host "Error: Not a git repository: $RepoPath" -ForegroundColor Red
        return
    }

    # Get git remote URL
    $remoteUrl = ""
    try {
        Push-Location $RepoPath
        $remoteUrl = git remote get-url origin 2>$null
    } catch {
        Write-Host "Warning: No 'origin' remote found. Adding without remote URL." -ForegroundColor Yellow
    } finally {
        Pop-Location
    }

    # Get repo name
    $repoName = Split-Path $RepoPath -Leaf

    $config = Get-Config
    $existing = $config.repos | Where-Object { $_.name -eq $repoName }

    $newEntry = @{
        name = $repoName
        remoteUrl = $remoteUrl
        addedFrom = $RepoPath
        addedAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    }

    if ($existing) {
        Write-Host "Repository '$repoName' is already tracked. Updating..." -ForegroundColor Yellow
        $config.repos = @($config.repos | Where-Object { $_.name -ne $repoName }) + $newEntry
    } else {
        $config.repos = @($config.repos) + $newEntry
    }

    Save-Config $config
    
    Write-Host "Added repository: $repoName" -ForegroundColor Green
    Write-Host "  Remote: $remoteUrl" -ForegroundColor Cyan
    Write-Host "  Path: $RepoPath"
}

# Remove a repo from tracking
function Remove-Repo {
    param([string]$RepoName)
    
    if ([string]::IsNullOrEmpty($RepoName)) {
        Write-Host "Error: Please provide a repository name" -ForegroundColor Red
        Write-Host "Usage: repo-manager.ps1 remove <name>"
        return
    }

    $config = Get-Config
    $existing = $config.repos | Where-Object { $_.name -eq $RepoName }

    if (-not $existing) {
        Write-Host "Repository '$RepoName' is not tracked" -ForegroundColor Red
        return
    }

    $config.repos = @($config.repos | Where-Object { $_.name -ne $RepoName })
    Save-Config $config

    Write-Host "Removed repository: $RepoName" -ForegroundColor Green
}

# List all tracked repos
function Get-Repos {
    Write-Host "Tracked Repositories:" -ForegroundColor Cyan
    Write-Host ("=" * 60)
    
    $config = Get-Config
    
    if ($config.repos.Count -eq 0) {
        Write-Host "No repositories tracked yet." -ForegroundColor Yellow
        Write-Host "Use 'repo-manager.ps1 add <path>' to add a repository."
        return
    }

    foreach ($repo in $config.repos) {
        Write-Host "  $($repo.name)" -ForegroundColor White
        Write-Host "    Remote: $($repo.remoteUrl)" -ForegroundColor Gray
        Write-Host "    Added: $($repo.addedAt)" -ForegroundColor Gray
        Write-Host ""
    }

    Write-Host ("=" * 60)
    Write-Host "Total: $($config.repos.Count) repositories" -ForegroundColor Green
}

# Sync/clone repos to current machine
function Sync-Repos {
    $basePath = Get-BasePath
    
    Write-Host "Syncing repositories to: $basePath" -ForegroundColor Cyan
    Write-Host ("=" * 60)

    $config = Get-Config
    
    if ($config.repos.Count -eq 0) {
        Write-Host "No repositories to sync." -ForegroundColor Yellow
        return
    }

    # Create base path if needed
    if (-not (Test-Path $basePath)) {
        New-Item -ItemType Directory -Path $basePath -Force | Out-Null
    }

    $synced = 0
    $skipped = 0
    $failed = 0

    foreach ($repo in $config.repos) {
        $targetPath = Join-Path $basePath $repo.name

        if (Test-Path $targetPath) {
            Write-Host "[SKIP] $($repo.name) (already exists at $targetPath)" -ForegroundColor Yellow
            $skipped++
            continue
        }

        if ([string]::IsNullOrEmpty($repo.remoteUrl)) {
            Write-Host "[FAIL] Cannot clone $($repo.name) (no remote URL)" -ForegroundColor Red
            $failed++
            continue
        }

        Write-Host "[CLONE] $($repo.name)..." -ForegroundColor Cyan
        try {
            git clone $repo.remoteUrl $targetPath
            Write-Host "[OK] Cloned $($repo.name)" -ForegroundColor Green
            $synced++
        } catch {
            Write-Host "[FAIL] Failed to clone $($repo.name): $_" -ForegroundColor Red
            $failed++
        }
    }

    Write-Host ("=" * 60)
    Write-Host "Synced: $synced | Skipped: $skipped | Failed: $failed"
}

# Show status of repos on current machine
function Get-RepoStatus {
    $basePath = Get-BasePath
    
    Write-Host "Repository Status (base: $basePath)" -ForegroundColor Cyan
    Write-Host ("=" * 60)

    $config = Get-Config
    $present = 0
    $missing = 0

    foreach ($repo in $config.repos) {
        $targetPath = Join-Path $basePath $repo.name

        if (Test-Path $targetPath) {
            Write-Host "[OK] $($repo.name)" -ForegroundColor Green
            $present++
        } else {
            Write-Host "[MISSING] $($repo.name)" -ForegroundColor Red
            $missing++
        }
    }

    Write-Host ("=" * 60)
    Write-Host "Present: $present | Missing: $missing"
}

# Scan workspace and add all git repos
function Invoke-Scan {
    param([string]$ScanPath)
    
    if ([string]::IsNullOrEmpty($ScanPath)) {
        $ScanPath = Get-BasePath
    }

    Write-Host "Scanning for git repositories in: $ScanPath" -ForegroundColor Cyan
    Write-Host ("=" * 60)

    $added = 0
    $gitDirs = Get-ChildItem -Path $ScanPath -Filter ".git" -Directory -Recurse -Depth 1 -ErrorAction SilentlyContinue

    foreach ($gitDir in $gitDirs) {
        $repoDir = $gitDir.Parent.FullName
        Write-Host "Found: $repoDir"
        Add-Repo $repoDir
        $added++
    }

    Write-Host ("=" * 60)
    Write-Host "Added $added repositories" -ForegroundColor Green
}

# Set base path for an OS
function Set-BasePath {
    param([string]$TargetOS, [string]$Path)

    if ([string]::IsNullOrEmpty($TargetOS) -or [string]::IsNullOrEmpty($Path)) {
        Write-Host "Error: Please provide OS and path" -ForegroundColor Red
        Write-Host "Usage: repo-manager.ps1 set-path <linux|darwin|windows> <path>"
        return
    }

    if ($TargetOS -notin @("linux", "darwin", "windows")) {
        Write-Host "Error: OS must be linux, darwin, or windows" -ForegroundColor Red
        return
    }

    $config = Get-Config
    $config.defaultBasePaths.$TargetOS = $Path
    Save-Config $config

    Write-Host "Set $TargetOS base path to: $Path" -ForegroundColor Green
}

# Show help
function Show-Help {
    Write-Host "Repo Manager" -ForegroundColor Cyan -NoNewline
    Write-Host " - Cross-platform repository synchronization"
    Write-Host ""
    Write-Host "Usage: repo-manager.ps1 <command> [args]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  add <path>              Add a repository to tracking"
    Write-Host "  remove <name>           Remove a repository from tracking"
    Write-Host "  list                    List all tracked repositories"
    Write-Host "  sync                    Clone missing repositories to this machine"
    Write-Host "  status                  Show which repos exist on this machine"
    Write-Host "  scan [path]             Scan directory and add all git repos found"
    Write-Host "  set-path <os> <path>    Set base path for an OS (linux/darwin/windows)"
    Write-Host "  help                    Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\repo-manager.ps1 add C:\dev\example.es"
    Write-Host "  .\repo-manager.ps1 scan C:\dev"
    Write-Host "  .\repo-manager.ps1 sync"
    Write-Host "  .\repo-manager.ps1 set-path linux '/home/user/repos'"
}

# Main
Initialize-Config

switch ($Command.ToLower()) {
    "add"      { Add-Repo $Arg1 }
    "remove"   { Remove-Repo $Arg1 }
    "list"     { Get-Repos }
    "sync"     { Sync-Repos }
    "status"   { Get-RepoStatus }
    "scan"     { Invoke-Scan $Arg1 }
    "set-path" { Set-BasePath $Arg1 $Arg2 }
    default    { Show-Help }
}

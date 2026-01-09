# Dev CLI - Development workflow tool (PowerShell)
# Usage: dev <subcommand> [args]

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Help {
    Write-Host "Dev CLI" -ForegroundColor Cyan -NoNewline
    Write-Host " - Development workflow tool"
    Write-Host ""
    Write-Host "Usage: dev <subcommand> [args]"
    Write-Host ""
    Write-Host "Subcommands:"
    Write-Host "  repo <command>    Manage tracked repositories"
    Write-Host "  help              Show this help message"
    Write-Host ""
    Write-Host "Repo commands:"
    Write-Host "  dev repo add <path>        Add a repository to tracking"
    Write-Host "  dev repo remove <name>     Remove a repository from tracking"
    Write-Host "  dev repo list              List all tracked repositories"
    Write-Host "  dev repo sync              Clone missing repositories"
    Write-Host "  dev repo status            Show which repos exist locally"
    Write-Host "  dev repo scan [path]       Scan and add all git repos"
    Write-Host "  dev repo set-path <os> <path>  Set base path for an OS"
}

switch ($Command.ToLower()) {
    "repo" {
        & "$ScriptDir\repo-manager.ps1" @Args
    }
    default {
        Show-Help
    }
}

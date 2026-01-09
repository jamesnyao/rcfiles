# Repo Manager
Cross-platform repository synchronization tool

## Overview

This tool helps you track repositories across multiple machines and operating systems. When you add a repo on one machine, you can sync it to other machines by running a simple command.

## Setup

### Linux/macOS

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
source ~/.repoconfig/aliases.sh
```

Or create a symlink:

```bash
sudo ln -s ~/.repoconfig/repo-manager.sh /usr/local/bin/repo
```

### Windows

Add the `.repoconfig` folder to your PATH, or create a PowerShell alias in your `$PROFILE`:

```powershell
Set-Alias repo "$env:USERPROFILE\.repoconfig\repo-manager.ps1"
```

## Usage

### Add a repository to tracking

```bash
# Linux/macOS
repo add ~/repos/example.es

# Windows
.\repo-manager.ps1 add C:\dev\example.es
```

### List tracked repositories

```bash
repo list
# or with alias:
get-repos
```

### Sync repositories to current machine

When you move to a new machine, run:

```bash
repo sync
# or with alias:
sync-repos
```

This will clone all tracked repositories that don't exist on the current machine.

### Check status

```bash
repo status
```

Shows which tracked repos exist on the current machine and which are missing.

### Scan and add all repos in a directory

```bash
repo scan /workspace
```

Finds all git repositories and adds them to tracking.

### Set base path for an OS

```bash
repo set-path windows "D:\repos"
repo set-path linux "/home/user/repos"
```

## Configuration

The configuration is stored in `repos.json`:

```json
{
  "version": 1,
  "defaultBasePaths": {
    "linux": "/workspace",
    "darwin": "/workspace",
    "windows": "C:\\dev"
  },
  "repos": [
    {
      "name": "example.es",
      "remoteUrl": "https://dev.azure.com/example/repo",
      "addedFrom": "/workspace/example.es",
      "addedAt": "2026-01-08T12:00:00Z"
    }
  ]
}
```

## Syncing the Config File

Since this lives in `~/.repoconfig`, you can:

1. **Add to your rcfiles repo**: Track it alongside your dotfiles
2. **Symlink from rcfiles**: `ln -s ~/rcfiles/.repoconfig ~/.repoconfig`
3. **Store in cloud sync**: Put in OneDrive/Dropbox and symlink

## Quick Reference

| Command | Description |
|---------|-------------|
| `repo add <path>` | Add a repo to tracking |
| `repo remove <name>` | Remove a repo from tracking |
| `repo list` | List all tracked repos |
| `repo sync` | Clone missing repos |
| `repo status` | Show repo status |
| `repo scan [path]` | Scan and add repos |
| `repo set-path <os> <path>` | Set base path |

---
name: dev-cli
description: >-
  Dev CLI (`dev` command) reference — repository management, cross-machine sync,
  Python management, and shell setup. Use when working with the dev CLI tool,
  managing tracked repos, or setting up a new machine.
---

# Dev CLI (`dev` command)

A cross-platform development workflow tool for managing repositories across machines. Located at `~/dev_scripts/dev.py`.

## Dev Scripts Structure

```
~/dev_scripts/
├── dev.py              # Main CLI (cross-platform)
├── dev                 # Linux launcher (bash)
├── aliases.sh          # Linux/macOS shell functions
├── python3             # Linux python shim (bash)
├── python3.cmd         # Windows python shim (batch)
└── repoconfig/
    ├── repos.json              # Tracked repos config
    ├── copilot-instructions.md # Synced copilot instructions
    └── ado_pat.txt             # Azure DevOps Personal Access Token
```

## Repository Management

```bash
# Add a repository to tracking
dev repo add <path>              # e.g., dev repo add edge/src

# Nested repos in gclient enlistments are auto-detected
dev repo add edge/src            # → tracked as "edge/src"
dev repo add cr/depot_tools      # → tracked as "cr/depot_tools"

# List all tracked repositories
dev repo list

# Check which repos exist on this machine
dev repo status

# Clone missing repositories to the base path
dev repo sync

# Scan a directory and add all git repos (including nested ones in gclient enlistments)
dev repo scan [path]

# Remove a repository from tracking
dev repo remove <name>

# Set base path for an OS
dev repo set-path <os> <path>    # os: linux, darwin, windows
```

## Repository Naming

- Top-level repos use their folder name: `sealion`, `releasebot`, `es`
- Repos inside gclient enlistments (`.gclient` present) use `parent/name` format:
  - `edge/src` - Edge chromium source
  - `cr/src` - Upstream Chromium source
  - `cr/depot_tools` - Chromium depot_tools

## Tracked Repositories

| Name | Description |
|------|-------------|
| `edge/src` | Edge Chromium source (main enlistment) |
| `cr/src` | Upstream Chromium source |
| `cr/depot_tools` | Chromium depot_tools |
| `es` | Edge Engineering Systems |
| `sealion` | Build pipeline pool management |
| `releasebot` | Release automation |

## Cross-Machine Sync

The config is stored in `~/dev_scripts/repoconfig/repos.json` and can be synced across machines. Running `dev repo sync` on a new machine will clone all tracked repos.

In addition to tracked files (`.github/copilot-instructions.md`, `.claude/CLAUDE.md`), `dev repo sync` automatically discovers and syncs all workspace-level skills under `.github/skills/`. Each skill directory (containing a `SKILL.md`) is bidirectionally synced using the same timestamp-based logic as other tracked files.

Default base paths by OS:
- **Linux**: `/workspace`
- **macOS**: `/workspace`
- **Windows**: `Q:\dev`

Use `dev repo set-path <os> <path>` to customize.

## Python Management

```bash
# Update Python to latest stable version (cross-platform)
dev python update
```

On Windows uses winget, on macOS uses Homebrew, on Linux uses apt/dnf.

## Shell Setup

### Linux/macOS (bash/zsh)

Add to `~/.bashrc` or `~/.zshrc`:
```bash
source ~/dev_scripts/aliases.sh
```

Available commands after sourcing:
- `set-downstream` - Use edge/depot_tools (depot_tools python, no shim)
- `set-internal` - Use edge/depot_tools (with python shim for system python)
- `set-upstream` - Use cr/depot_tools (with python shim)
- `set-crdt` - Use cr/depot_tools (with python shim)
- `reset-path` - Reset PATH to original

The python shim (`~/dev_scripts/python3`) skips depot_tools/scripts python and finds the real system python.

### Windows (PowerShell)

Functions defined in `$PROFILE`:
- `Set-Downstream` - Use edge\depot_tools (depot_tools python, no shim)
- `Set-Internal` - Use edge\depot_tools (with python shim)
- `Set-Upstream` - Use cr\depot_tools (with python shim)
- `Set-CrDT` - Use cr\depot_tools (with python shim)

The python shim (`~/dev_scripts/python3.cmd`) skips depot_tools\scripts and Windows Store stubs.

## Azure DevOps

For ADO operations (PRs, builds, work items), use the **edge-ado plugin skills** (`pr`, `pipeline`, `workitem`) which authenticate via `es login` or `az login`.

The file `~/dev_scripts/repoconfig/ado_pat.txt` stores a PAT used by the dev CLI itself for ADO API calls. If the PAT is expired or missing, prompt the user to update it with `dev ado set-pat`.

# Dev CLI

A cross-platform development workflow tool for managing repositories across machines. Located at `~/.dev_scripts/dev.py`.

## Critical Rules

**ALWAYS run tests after modifying `~/.dev_scripts/`.** If any file in the `~/.dev_scripts/` directory (including `dev.py`, `test_dev.py`, or any repoconfig files) is modified, you MUST run `python3 ~/.dev_scripts/test_dev.py` and ensure ALL tests pass before considering the change complete. This is non-negotiable.

**ALWAYS validate fixes.** After making any fix, test and validate the change actually works. For `~/.dev_scripts/` changes: run `python3 ~/.dev_scripts/test_dev.py` (all tests must pass), then run `dev repo sync` to verify end-to-end behavior.

## Code Cleanup Guidelines

When asked to do code cleanup:
- **Simplify function documentation** to about a single sentence unless the function REALLY needs a more complex description
- **Remove all inline comments** unless they explain convoluted code
- **Clean up unused usings/includes/imports**
- **Clean up unnecessary namespace prefixes** (e.g., `System.IO.File` → `File`) if not required

## Workspace Paths

The workspace root differs by operating system:
- **Linux/macOS**: `/workspace`
- **Windows**: `C:\dev` (or other drive letter)

Use `dev repo set-path <os> <path>` to customize.

## Dev Scripts Structure

```
~/.dev_scripts/
├── dev.py              # Main CLI (cross-platform)
├── dev                 # Linux launcher (bash)
├── test_dev.py         # Tests (run after ANY change)
├── aliases.sh          # Linux/macOS shell functions
├── python3             # Linux python shim (bash)
├── python3.cmd         # Windows python shim (batch)
└── repoconfig/
    ├── repos.json              # Tracked repos config
    ├── copilot-instructions.md # Synced copilot instructions
    └── CLAUDE.md               # Synced Claude instructions
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

### Repository Naming

- Top-level repos use their folder name: `sealion`, `releasebot`, `es`
- Repos inside gclient enlistments (`.gclient` present) use `parent/name` format:
  - `edge/src`, `cr/src`, `cr/depot_tools`

### Cross-Machine Sync

The config is stored in `~/.dev_scripts/repoconfig/repos.json` and can be synced across machines. Running `dev repo sync` on a new machine will clone all tracked repos.

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
source ~/.dev_scripts/aliases.sh
```

Available commands after sourcing:
- `set-downstream` - Use edge/depot_tools (depot_tools python, no shim)
- `set-internal` - Use edge/depot_tools (with python shim for system python)
- `set-upstream` - Use cr/depot_tools (with python shim)
- `set-crdt` - Use cr/depot_tools (with python shim)
- `reset-path` - Reset PATH to original

The python shim (`~/.dev_scripts/python3`) skips depot_tools/scripts python and finds the real system python.

### Windows (PowerShell)

Functions defined in `$PROFILE`:
- `Set-Downstream` - Use edge\depot_tools (depot_tools python, no shim)
- `Set-Internal` - Use edge\depot_tools (with python shim)
- `Set-Upstream` - Use cr\depot_tools (with python shim)
- `Set-CrDT` - Use cr\depot_tools (with python shim)

The python shim (`~/.dev_scripts/python3.cmd`) skips depot_tools\scripts and Windows Store stubs.

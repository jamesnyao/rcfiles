# Copilot Instructions

This workspace contains multiple repositories for Microsoft Edge infrastructure and build systems.
Update this file with any relevant information that would help Copilot provide better suggestions.
Review any deletions to this file - unless the information is no longer accurate.

**If this file contains merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), resolve them immediately.** Analyze both versions, preserve all valuable content from each side, fix any typos, and remove the conflict markers. Prefer the version with more detail or corrections. After resolving, ensure the file is valid markdown. (Note: The markers shown in this rule as examples are not actual conflicts.)

## Critical Rules

**NEVER interrupt a running build unless explicitly asked or there are actual errors.** When a build is in progress and has not generated errors, let it complete. Build interruptions waste significant time and resources.
**CONTINUOUSLY monitor a running build for errors - only interrupt if necessary.** 
Continuously monitor the build for errors by checking the terminal output every 30 seconds, if timeouts are detected and cause the build to fail, restart the build. If other errors are detected, make the appropriate changes to fix the errors and restart the build. Check for build logs in `edge/src/out/siso*`.

**ALWAYS run tests after modifying `~/.dev_scripts/`.** If any file in the `~/.dev_scripts/` directory (including `dev.py`, `test_dev.py`, or any repoconfig files) is modified, you MUST run `python3 ~/.dev_scripts/test_dev.py` and ensure ALL tests pass before considering the change complete. This is non-negotiable.

## Workspace Paths

The workspace root differs by operating system:
- **Linux/macOS**: `/workspace`
- **Windows**: `Q:\dev` (or other drive letter)

All paths in this document are relative to the workspace root.

## Repository Structure

### `edge/src` - Edge Chromium Source (chromium.src)
The main Edge/Chromium source code repository. The base `edge/` is the Edge gclient enlistment.

**Key directories:**
- `anaheim/pipelines/` - Azure DevOps pipeline definitions for Edge builds
  - `templates/` - Reusable pipeline templates
  - `ios-official-candidate.yml` - iOS candidate build pipeline
  - `ios-official-promotion.yml` - iOS promotion/signing pipeline
- `ios/chrome/` - iOS-specific Chrome/Edge code
  - `*/entitlements/` - iOS app entitlements files
  - `open_extension/`, `action_extension/`, `share_extension/` etc. - App extensions
- `ios/build/chrome_build.gni` - iOS build configuration flags

**External repos referenced by pipelines:**
- `Edge/edgeinternal.es.sealion` - Pipeline templates (referenced via `sealion-pipeline-template.yml`)
- `Edge/edgeinternal.es.ios.mobileprovision` - iOS provisioning profiles

### `cr/src` - Upstream Chromium Source
Vanilla Chromium source for reference. The base `cr/` is a gclient enlistment.

### `cr/depot_tools` - Chromium Depot Tools
Google's depot_tools (gclient, gn, ninja wrappers). Edge-specific fork is at `chromium.depot_tools.cr-contrib`.

### `es/` - Edge Engineering Systems (edgeinternal.es)
Infrastructure, tooling, and Azure resource management.

**Key directories:**
- `RE/` - Remote Execution infrastructure
  - `AzurePipelines/` - Pipeline definitions for RE operations
  - `AzureScripts/` - PowerShell scripts for Azure resource management
  - `AzureTemplates/` - Bicep templates for Azure infrastructure
- `sealion/` - Build pipeline pool management
- `cipd/` - Chrome Infrastructure Package Deployment tools
- `isolateservice/` - Isolate service for build caching

### `sealion/` - Build Pipeline Pool Management
Standalone repo for Sealion pipeline templates.

### `releasebot/` - Release Automation
Release automation tooling.

## Common Patterns

### Azure DevOps Pipelines
- Use 1ES Pipeline Templates (`1ESPipelineTemplates/1ESPipelineTemplates`)
- Pipeline parameters use `${{ parameters.Name }}` syntax
- Variables use `$(VariableName)` syntax
- Boolean parameters expand to lowercase `true`/`false` in bash scripts

### iOS Build/Signing Flow
1. **Candidate build** (`ios-official-candidate.yml`) creates artifacts including:
   - `Edge-official.zip` - The app bundle
   - `Edge-official-entitlements.zip` - Entitlements for signing
2. **Promotion pipeline** (`ios-official-promotion.yml`) signs for different channels
3. Entitlements are in `entitlements/<extension>.entitlements` format
4. Provisioning profiles come from `edgeinternal.es.ios.mobileprovision` repo

### Azure Resources (RE/)
- Storage accounts: Named with pattern `<basename><suffix>` (e.g., `rbestoragedev00` - `rbestoragedevff`)
- Deployment targets: Preprod, Staging, Prod, Official
- Uses Bicep for infrastructure as code
- Scripts in `AzureScripts/` use PowerShell Core

### Testing on RE Preprod
To test changes on RE Preprod, use:
```bash
set_re_dev; set_remote_only; autoninja -C out/linux_x64_debug_developer_build chrome
```
- `set_re_dev` - Points to the RE Preprod environment
- `set_remote_only` - Prevents local fallbacks from polluting the output and giving false positive build results

**Note:** If testing a preprod build with fallbacks disabled and the build fails purely due to timeouts, restart the build. This is caused by high load and is not indicative of 500 errors.

## File Naming Conventions

- Pipeline files: `<platform>-<purpose>.yml`
- Entitlements: `<extension_name>.appex.entitlements`
- Bicep templates: `template-<resource-type>.bicep`
- PowerShell scripts: `Verb-Noun.ps1` (e.g., `Deploy-AzureResources.ps1`)

## Quick Reference

| Task | Location |
|------|----------|
| iOS pipeline issues | `edge/src/anaheim/pipelines/templates/ios-*.yml` |
| RE/Build infrastructure | `es/RE/` |
| iOS entitlements | `edge/src/ios/chrome/*/entitlements/` |
| Build flags | `edge/src/ios/build/chrome_build.gni` |
| Azure resources | `es/RE/AzureTemplates/*.bicep` |
| Dev CLI scripts | `~/.dev_scripts/dev.py` |
| Repo tracking config | `~/.dev_scripts/repoconfig/repos.json` |
| Copilot instructions sync | `~/.dev_scripts/repoconfig/copilot-instructions.md` |
| ADO PAT (PRs, builds, API) | `~/.dev_scripts/repoconfig/ado_pat.txt` |

### Dev Scripts Structure

```
~/.dev_scripts/
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

### Azure DevOps PAT

The file `~/.dev_scripts/repoconfig/ado_pat.txt` stores an Azure DevOps Personal Access Token (PAT) used for authenticated ADO API requests including:
- **Pull Requests** - Creating, querying, and managing PRs
- **Build Logs** - Fetching build logs and pipeline results
- **Other ADO Requests** - Work items, artifacts, and general ADO REST API calls

**If the PAT is expired or returns authentication errors, prompt the user to provide a new PAT and update the file.**

## Dev CLI (`dev` command)

A cross-platform development workflow tool for managing repositories across machines. Located at `~/.dev_scripts/dev.py`.

### Repository Management

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
  - `edge/src` - Edge chromium source
  - `cr/src` - Upstream Chromium source  
  - `cr/depot_tools` - Chromium depot_tools

### Tracked Repositories

| Name | Description |
|------|-------------|
| `edge/src` | Edge Chromium source (main enlistment) |
| `cr/src` | Upstream Chromium source |
| `cr/depot_tools` | Chromium depot_tools |
| `es` | Edge Engineering Systems |
| `sealion` | Build pipeline pool management |
| `releasebot` | Release automation |

### Cross-Machine Sync

The config is stored in `~/.dev_scripts/repoconfig/repos.json` and can be synced across machines. Running `dev repo sync` on a new machine will clone all tracked repos.

Default base paths by OS:
- **Linux**: `/workspace`
- **macOS**: `/workspace`
- **Windows**: `Q:\dev`

Use `dev repo set-path <os> <path>` to customize.

### Python Management

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

## PowerShell Terminal Guidelines

### CRITICAL: Never Source Profile
**NEVER** run `. $PROFILE` or `Import-Module` commands that wait for user input in the terminal. This will freeze Copilot chat indefinitely since it waits for a return value that never appears.

Instead, if you need to update a function or alias after modifying the profile:
- Define the function/alias directly in the current session
- Example: `function dev { python3 "$env:USERPROFILE\.dev_scripts\dev.py" @args }`

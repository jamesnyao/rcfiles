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

**ALWAYS validate fixes.** After making any fix, test and validate the change actually works. For `~/.dev_scripts/` changes: run `python3 ~/.dev_scripts/test_dev.py` (all tests must pass), then run `dev repo sync` to verify end-to-end behavior. For other fixes: run the relevant command, build, or test to confirm the fix works as expected.

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
  - `msRemoteExecution/` - .NET Remote Execution service and worker
- `sealion/` - Build pipeline pool management
- `cipd/` - Chrome Infrastructure Package Deployment tools
- `isolateservice/` - Isolate service for build caching

### `es2/` - Edge Engineering Systems v2 (development branch)
Development branch of Edge Engineering Systems with RE improvements.

**Key directories:**
- `RE/msRemoteExecution/` - Remote Execution .NET solution
  - `msRemoteExecution.Common/` - Shared RE library
  - `msRemoteExecution.Tests/` - Unit tests for RE
  - `msRemoteExecution.Worker/` - RE worker service

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

## Remote Execution (RE) Architecture

Edge uses a Bazel-compatible Remote Execution system for distributed clang/python builds. The RE service runs on Azure Kubernetes Service (AKS) and executes build actions sent from developer machines and CI.

### RE Solution Structure

```
es2/RE/msRemoteExecution/
├── msRemoteExecution/              # ASP.NET Core host (Program.cs, startup)
├── msRemoteExecution.Common/       # Shared library (all business logic)
│   ├── Services/                   # gRPC service implementations
│   │   ├── ExecutionService.cs     # Execute RPC endpoint
│   │   ├── ActionCacheService.cs   # Action cache lookups
│   │   ├── ByteStreamService.cs    # Blob streaming
│   │   └── ContentAddressableStorageService.cs
│   ├── Builder/                    # Execution orchestration
│   │   ├── RemoteExecutionOperationHandler.cs  # Entry point for Execute
│   │   ├── LocalExecutionOperationHandler.cs   # Local execution flow
│   │   └── QueueOperationService.cs            # macOS deferral to Service Bus
│   ├── ExecuteHelpers/             # Process execution
│   │   ├── ExecuteStage.cs         # Abstract base + ExecuteStageUnix
│   │   ├── ToolInfoFactory.cs      # Tool detection (Clang, Python)
│   │   ├── ToolsSetup.cs           # Toolchain download from CIPD
│   │   └── Toolchains/             # LlvmToolchain, PythonToolchain
│   ├── CAS/                        # Content Addressable Storage
│   │   ├── InputCacheManager.cs    # Materialize input trees
│   │   ├── AzureBlobProvider.cs    # Azure Blob Storage client
│   │   ├── KnownDirectories.cs     # Standard paths (/mnt/cache, etc.)
│   │   └── DiskFileProvider.cs     # Local SSD cache
│   └── FileSystemHelpers/          # Path translation, symlinks
│       ├── PathHelper.cs           # Windows↔Unix path conversion
│       └── LocalSourceDirectory.cs # Per-action working directory
└── msRemoteExecution.Tests/        # Unit tests
    ├── ExecuteHelpers/ExecuteStageTests.cs
    └── Mocks/                      # TestableExecuteStageUnix, etc.
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| ExecutionService | `Services/` | gRPC endpoint, receives ExecuteRequest |
| RemoteExecutionOperationHandler | `Builder/` | Checks action cache, routes to local/mac |
| LocalExecutionOperationHandler | `Builder/` | Orchestrates ToolsSetup → FilesSetup → ExecuteStage |
| ExecuteStage/ExecuteStageUnix | `ExecuteHelpers/` | Builds ProcessStartInfo, runs clang/python |
| InputCacheManager | `CAS/` | Downloads input tree from CAS to local disk |
| ToolsSetup | `ExecuteHelpers/` | Downloads clang/python from CIPD cache |
| ToolInfoFactory | `ExecuteHelpers/` | Detects tool type from command (Clang Cl, Clang Gcc, Python) |

### RE Request Flow (End-to-End)

```
Client (reclient/ninja) 
    │
    ▼
ExecutionService.Execute(ExecuteRequest)
    │
    ▼
RemoteExecutionOperationHandler.ExecuteAsync
    ├── Check ActionCache (return cached result if hit)
    ├── Fetch Action + Command protos from CAS
    ├── If macOS target → QueueOperationService (Service Bus)
    └── Else → LocalExecutionOperationHandler.ExecuteAsync
                    │
                    ▼
              ToolsSetup.SetupAsync
              (Download clang/python from CIPD)
                    │
                    ▼
              FilesSetup.SetupAsync
              (Materialize input tree via InputCacheManager)
                    │
                    ▼
              ExecuteStage.ExecuteAsync
              ├── BuildArguments (arg transformation)
              ├── Path translation (Windows→Unix if cross-compile)
              ├── Trusted: WrapCommandWithBash
              ├── Untrusted: WrapCommandInDifferentUserNamespace (unshare)
              ├── RunProcessAsync (fork clang/python)
              └── Collect outputs → PackageOutputFile → CAS
                    │
                    ▼
              ActionCacheManager.PutActionCacheResult
                    │
                    ▼
              Return ExecuteResponse to client
```

### ExecuteStage.ExecuteAsync Deep Dive

The `ExecuteAsync` method in `ExecuteStage.cs` is the core execution logic:

```csharp
// Key decision points in ExecuteAsync:

1. Output Registration (lines 130-137)
   - Registers expected OutputFiles and OutputDirectories
   - Creates output directories if needed

2. ProcessStartInfo Setup (lines 140-156)
   - Calls BuildArguments (transforms args, handles Python literal args)
   - Sets WorkingDirectory via PathHelper translation
   - Sets FileName: relative path → translate, bare name → use LocalToolPath

3. Trusted vs Untrusted Execution (lines 165-211)
   - UntrustedBinaryOrScriptExecution = true (Python scripts):
     * Copies /lib, /lib64, /usr/lib, /usr/lib64 to chroot
     * Calls WrapCommandInDifferentUserNamespace (unshare -U --net -R)
   - UntrustedBinaryOrScriptExecution = false (Clang, trusted tools):
     * Calls WrapCommandWithBash for relative path execution
     * Python uses literal args (no bash wrapping)

4. Process Execution (line 227)
   - 10-minute timeout (ActionExecTimeout)
   - TelemetryCancellableProcess handles stdout/stderr capture

5. Output Collection (lines 235-260)
   - TelemetryOutputFileCollector scans for outputs
   - PackageOutputFile uploads to CAS
```

### BuildArguments Logic (ExecuteStageUnix)

```csharp
// Key transformations in BuildArguments:

1. First argument (tool path) is skipped
2. If TargetOS == "Windows":
   - Replace '\' with Path.DirectorySeparatorChar
   - EXCEPT for -D defines (protected by regex)
3. Python tools: use literal Arguments string
4. Clang tools: use ArgumentList collection
```

### Trusted vs Untrusted Execution

| Execution Mode | When Used | Process Wrapper | Example |
|---------------|-----------|-----------------|---------|
| **Trusted** | Clang (LLVM toolchain) | `/bin/bash -c "<tool> \"$@\" -- <args>"` | Clang from CIPD |
| **Untrusted** | Python scripts | `unshare -U --net -R <chroot> <tool>` | mojom generator |
| **Trusted Python** | macOS (override) | No wrapper, literal args | Python on macOS |

Python uses `UseLiteralArguments()` which sets `processStartInfo.Arguments` directly (not ArgumentList) to preserve special characters.

### Cross-Compilation (Linux→Windows)

Edge builds Windows binaries on Linux RE workers:

```csharp
// In BuildArguments, when TargetOS == "Windows":
argument = argument.Replace('\\', Path.DirectorySeparatorChar);

// In ExecuteAsync untrusted path:
var newWorkingDir = RootDirectory +
    (context.TargetPlatform == OSPlatform.Windows 
        ? PathHelper.TranslateWindowsPathToUnixPath(req.WorkingDirectory) 
        : req.WorkingDirectory);

// TranslateWindowsPathToUnixPath: C:\foo → /c/foo
```

### Key Platform Properties

Commands include `Platform.Properties` that control behavior:

| Property | Example Values | Used By |
|----------|---------------|---------|
| `llvm_version` | `llvmorg-18-init-12345-gabcdef12-1` | LlvmToolchain |
| `python_version` | `3.11.0` | PythonToolchain |
| `cipd_version` | `1.0.0` | Both toolchains |
| `TargetOS` | `Windows`, `Linux`, `macOS` | BuildArguments path handling |
| `OSFamily` | `linux`, `darwin`, `windows` | macOS deferral decision |

### Known Directories (KnownDirectories.cs)

| Directory | Linux Path | Purpose |
|-----------|------------|---------|
| LocalWorkRootDirectory | `/mnt/nvme/msRemoteExecutionWork` | Per-action working dirs |
| LocalSourceDirectory | `<work>/<guid>` | Materialized input tree |
| LocalCacheRootDirectory | `/mnt/nvme/msRemoteExecutionCache` | Persistent cache |
| LocalInputCacheDirectory | `<cache>/Input` | Downloaded input blobs |
| LocalToolsDirectory | `<cache>/Tools` | CIPD-downloaded tools |

### Azure Infrastructure

| Resource | Purpose |
|----------|---------|
| AKS Cluster | Hosts RE pods (Linux workers) |
| Azure Blob Storage | CAS (256 sharded storage accounts) |
| Redis Cache | CAS lookup cache, auth cache |
| Service Bus | macOS job queueing |
| App Insights | Telemetry and logging |

Storage account naming: `<prefix><shard>` where shard is 00-FF (256 accounts).

### Common Error Scenarios

| Error | Cause | Resolution |
|-------|-------|------------|
| `Could not find any output files` | Compilation succeeded but no .o/.obj found | Check OutputFiles in Command |
| `ActionExec Queue timeout` | Semaphore wait > 2 minutes | High load, retry |
| `Missing ActionDigest` | Blob not in CAS | Client upload issue |
| `Process timeout` | Compilation > 10 minutes | Increase timeout or check action |
| `unshare: operation not permitted` | Missing CAP_SYS_ADMIN | Container security context |

### Testing RE Code

```bash
# Run all RE tests
cd es2/RE/msRemoteExecution
dotnet test

# Run specific test
dotnet test --filter "FullyQualifiedName~ExecuteAsync"

# Build only
dotnet build
```

Key test patterns:
- **TestableExecuteStageUnix**: Subclass that captures ProcessStartInfo without execution
- **skipProcessExecution=true**: Test command building on Windows
- **MockKnownDirectoriesFactory**: Creates KnownDirectories with temp paths
- **TestableExecuteStageFactory.Create()**: Full test setup with mocks

### RE Environments

| Environment | Purpose | How to Use |
|-------------|---------|------------|
| Preprod | Testing RE changes | `set_re_dev` |
| Staging | Pre-production validation | Internal |
| Prod | Production builds | Default |
| Official | Official/signed builds | CI only |

## Chromium/Edge Build Specifics

### RE Must Handle These Patterns

| Pattern | Example | Why It Matters |
|---------|---------|----------------|
| Deep nesting | `third_party/blink/renderer/core/layout/inline/` | 10+ directory levels |
| Toolchain symlinks | `clang++` → `clang`, `clang-cl` → `clang` | Must create symlinks after files |
| Many inputs | 1000+ files per compile action | Performance critical |
| Python codegen | `gen/mojo/public/tools/bindings/mojom_bindings_generator.py` | Literal arg preservation |
| Long command lines | 100+ `-I` flags, 50+ `-D` defines | Argument parsing |
| OutputDirectories | Code generators like protoc | Not just OutputFiles |

### Clang Command Line Flags (Edge)

```bash
# Target architecture (cross-compilation)
--target=x86_64-unknown-linux-gnu
--target=aarch64-apple-darwin
--target=x86_64-pc-windows-msvc  # Linux→Windows cross-compile

# Edge-specific defines (DO NOT modify backslashes in -D values!)
-DOFFICIAL_BUILD
-DEDGE_CHANNEL_STABLE
-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE
-DPROTOBUF_DISABLE_PROTO3_LITE_RUNTIME_COMPATIBILITY

# Relative tool paths (common in Edge)
../../third_party/llvm-build/Release+Asserts/bin/clang
../../third_party/llvm-build/Release+Asserts/bin/clang-cl

# Include paths
-I../../base -I../../build -Igen -I../../third_party/abseil-cpp

# Modulemaps (requires hard links in toolchain, not symlinks)
-fmodule-map-file=gen/base/base_module.modulemap
```

### Python (Mojom/Mojo) Command Patterns

Mojom generator and other Python tools use literal arguments:

```bash
# Mojom binding generator (NEVER escape these args)
python3 gen/mojo/public/tools/bindings/mojom_bindings_generator.py \
  --output_dir=gen \
  --typemap=gen/mojo/public/tools/bindings/blink_bindings.typemap \
  -- \
  third_party/blink/public/mojom/page/page.mojom

# Protocol buffer compiler (uses OutputDirectories)
python3 ../../third_party/protobuf/python/google/protobuf/compiler/plugin.py \
  --output=gen/components/autofill/core
```

### Path Translation Behavior

```csharp
// RE must translate client paths to worker paths

// Windows client → Linux worker (cross-compilation)
"C:\\chromium\\src\\base\\file.cc" → "/chromium/src/base/file.cc"

// Relative paths with backslashes → forward slashes
"..\\..\\third_party\\llvm-build\\bin\\clang" → "../../third_party/llvm-build/bin/clang"

// EXCEPTION: -D defines preserve backslashes (regex protected)
"-DPATH=C:\\foo\\bar" → "-DPATH=C:\\foo\\bar"  // Unchanged!
```

### Build Configurations

```bash
# Developer build (debug, non-official)
gn gen out/linux_x64_debug_developer_build

# Official build (release, signing)
gn gen out/Official

# Component build (faster linking)
is_component_build = true

# RE-enabled build
use_remoteexec = true
reclient_cfg_dir = "//buildtools/reclient_cfgs/linux"
```

## File Naming Conventions

- Pipeline files: `<platform>-<purpose>.yml`
- Entitlements: `<extension_name>.appex.entitlements`
- Bicep templates: `template-<resource-type>.bicep`
- PowerShell scripts: `Verb-Noun.ps1` (e.g., `Deploy-AzureResources.ps1`)

## Quick Reference

| Task | Location |
|------|----------|
| iOS pipeline issues | `edge/src/anaheim/pipelines/templates/ios-*.yml` |
| RE/Build infrastructure | `es/RE/` or `es2/RE/` |
| RE .NET service code | `es2/RE/msRemoteExecution/msRemoteExecution.Common/` |
| RE unit tests | `es2/RE/msRemoteExecution/msRemoteExecution.Tests/` |
| InputCacheManager | `msRemoteExecution.Common/CAS/InputCacheManager.cs` |
| ExecuteStage | `msRemoteExecution.Common/ExecuteHelpers/ExecuteStage.cs` |
| TestableExecuteStageUnix | `msRemoteExecution.Tests/Mocks/TestableExecuteStageUnix.cs` |
| MockKnownDirectories | `msRemoteExecution.Tests/Mocks/MockKnownDirectories.cs` |
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

**IMPORTANT: If the PAT is expired or returns authentication errors, or is missing, prompt the user to provide a new PAT and update the file.**

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


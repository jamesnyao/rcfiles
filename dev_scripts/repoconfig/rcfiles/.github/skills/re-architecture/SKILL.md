---
name: re-architecture
description: >-
  Remote Execution (RE) architecture — solution structure, request flow, execution logic,
  cross-compilation, Preprod testing, and Chromium/Edge build patterns.
  Use when working on RE code in es2/RE/msRemoteExecution.
---

# Remote Execution (RE) Architecture

Bazel-compatible RE system for distributed clang/python builds, running on AKS. Executes build actions from developer machines and CI.

The client-side build orchestrator is **siso**, sourced from chromium.infra.build (https://dev.azure.com/microsoft/Edge/_git/chromium.infra.build) (`mirror/main` branch). Reference this repo for siso behavior, reclient integration, and build request formatting.

## Solution Structure

All business logic is in `msRemoteExecution.Common/`:

| Directory | Key Files | Purpose |
|-----------|-----------|---------|
| `Services/` | ExecutionService, ActionCacheService, ByteStreamService, ContentAddressableStorageService | gRPC endpoints |
| `Builder/` | RemoteExecutionOperationHandler, LocalExecutionOperationHandler, QueueOperationService | Execution orchestration, macOS deferral to Service Bus |
| `ExecuteHelpers/` | ExecuteStage (abstract + ExecuteStageUnix), ToolInfoFactory, ToolsSetup, Toolchains/ | Process execution, tool detection (Clang Cl/Gcc, Python), CIPD download |
| `CAS/` | InputCacheManager, AzureBlobProvider, KnownDirectories, DiskFileProvider | Content Addressable Storage, input materialization, local SSD cache |
| `FileSystemHelpers/` | PathHelper, LocalSourceDirectory | Windows↔Unix path conversion, per-action working dirs |

Tests: `msRemoteExecution.Tests/` — `ExecuteStageTests.cs`, mocks in `Mocks/` (TestableExecuteStageUnix, MockKnownDirectoriesFactory)

## Request Flow

```
Client (reclient/ninja)
  → ExecutionService.Execute(ExecuteRequest)
  → RemoteExecutionOperationHandler.ExecuteAsync
      ├─ ActionCache hit → return cached result
      ├─ macOS target → QueueOperationService (Service Bus)
      └─ LocalExecutionOperationHandler.ExecuteAsync
           1. ToolsSetup.SetupAsync — download clang/python from CIPD
           2. FilesSetup.SetupAsync — materialize input tree via InputCacheManager
           3. ExecuteStage.ExecuteAsync — build args, run process, collect outputs
  → ActionCacheManager.PutActionCacheResult
  → Return ExecuteResponse
```

## ExecuteStage.ExecuteAsync

Core execution logic in `ExecuteStage.cs`:

1. **Output registration** — register expected OutputFiles/OutputDirectories, create dirs
2. **ProcessStartInfo** — call BuildArguments, set WorkingDirectory (PathHelper translation), set FileName (relative path → translate, bare name → LocalToolPath)
3. **Execution mode** (see table below)
4. **Run process** — 10-minute timeout (ActionExecTimeout), TelemetryCancellableProcess captures stdout/stderr
5. **Collect outputs** — TelemetryOutputFileCollector → PackageOutputFile → upload to CAS

### BuildArguments (ExecuteStageUnix)

- First argument (tool path) is skipped
- If `TargetOS == "Windows"`: replace `\` with `Path.DirectorySeparatorChar`, EXCEPT `-D` defines (regex protected)
- Python tools: `UseLiteralArguments()` sets `processStartInfo.Arguments` directly (preserves special chars)
- Clang tools: uses `ArgumentList` collection

### Execution Modes

| Mode | When | Wrapper |
|------|------|---------|
| **Trusted** | Clang (LLVM) | `/bin/bash -c "<tool> \"$@\" -- <args>"` |
| **Untrusted** | Python scripts | Copies /lib, /lib64 to chroot, then `unshare -U --net -R <chroot> <tool>` |
| **Trusted Python** | macOS override | No wrapper, literal args |

## Cross-Compilation (Linux→Windows)

```csharp
// BuildArguments: backslash → forward slash (except -D defines)
argument = argument.Replace('\\', Path.DirectorySeparatorChar);

// WorkingDirectory: TranslateWindowsPathToUnixPath converts C:\foo → /c/foo
var newWorkingDir = RootDirectory +
    (context.TargetPlatform == OSPlatform.Windows
        ? PathHelper.TranslateWindowsPathToUnixPath(req.WorkingDirectory)
        : req.WorkingDirectory);
```

## Platform Properties

| Property | Example | Used By |
|----------|---------|---------|
| `llvm_version` | `llvmorg-18-init-12345-gabcdef12-1` | LlvmToolchain |
| `python_version` | `3.11.0` | PythonToolchain |
| `cipd_version` | `1.0.0` | Both toolchains |
| `TargetOS` | `Windows`, `Linux`, `macOS` | BuildArguments path handling |
| `OSFamily` | `linux`, `darwin`, `windows` | macOS deferral decision |

## Known Directories

| Directory | Path | Purpose |
|-----------|------|---------|
| LocalWorkRootDirectory | `/mnt/nvme/msRemoteExecutionWork` | Per-action working dirs |
| LocalSourceDirectory | `<work>/<guid>` | Materialized input tree |
| LocalCacheRootDirectory | `/mnt/nvme/msRemoteExecutionCache` | Persistent cache |
| LocalInputCacheDirectory | `<cache>/Input` | Downloaded input blobs |
| LocalToolsDirectory | `<cache>/Tools` | CIPD-downloaded tools |

## Azure Infrastructure

AKS hosts RE pods (Linux workers). CAS uses 256 sharded Azure Blob Storage accounts (`<prefix><00-FF>`). Redis for CAS/auth lookup cache. Service Bus for macOS job queueing. App Insights for telemetry.

## Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `Could not find any output files` | No .o/.obj found after compilation | Check OutputFiles in Command |
| `ActionExec Queue timeout` | Semaphore wait > 2 min | High load, retry |
| `Missing ActionDigest` | Blob not in CAS | Client upload issue |
| `Process timeout` | Compilation > 10 min | Increase timeout or check action |
| `unshare: operation not permitted` | Missing CAP_SYS_ADMIN | Container security context |

## Testing RE Code

```bash
cd es2/RE/msRemoteExecution
dotnet test                                          # all tests
dotnet test --filter "FullyQualifiedName~ExecuteAsync"  # specific test
dotnet build                                         # build only
```

Test patterns: **TestableExecuteStageUnix** captures ProcessStartInfo without execution. **skipProcessExecution=true** for command-building tests on Windows. **MockKnownDirectoriesFactory** creates temp paths. **TestableExecuteStageFactory.Create()** provides full mock setup.

## RE Environments & Preprod Testing

| Environment | REAPI_ADDRESS | REAPI_CAS_ADDRESS |
|-------------|---------------|-------------------|
| **Preprod** | `rbedev.westus3.cloudapp.azure.com:443` | `rbecasdev.westus3.cloudapp.azure.com:443` |
| **Prod** | Default (no override) | Default (no override) |
| **Staging** | Internal | Internal |
| **Official** | CI only | CI only |

To test on Preprod with no local fallbacks:

Linux:
```bash
export REAPI_ADDRESS="rbedev.westus3.cloudapp.azure.com:443"
export REAPI_CAS_ADDRESS="rbecasdev.westus3.cloudapp.azure.com:443"
export SISO_LIMITS="fastlocal=0,local=1,remote=24"
export SISO_EXPERIMENTS="no-fallback"
autoninja -C out/linux_x64_debug_developer_build chrome
```

Windows:
```powershell
$env:REAPI_ADDRESS = "rbedev.westus3.cloudapp.azure.com:443"
$env:REAPI_CAS_ADDRESS = "rbecasdev.westus3.cloudapp.azure.com:443"
$env:SISO_LIMITS = "fastlocal=0,local=1,remote=24"
$env:SISO_EXPERIMENTS = "no-fallback"
autoninja -C out\win_x64_debug_developer_build chrome
```

Omit `SISO_EXPERIMENTS` to allow local fallbacks. If the build fails purely due to timeouts with no-fallback, restart — it's high load, not 500 errors.

## Chromium/Edge Build Patterns

Patterns RE must handle: deep nesting (10+ levels), toolchain symlinks (`clang++` → `clang`), 1000+ input files per action, Python codegen with literal args, 100+ `-I`/`-D` flags, OutputDirectories (not just OutputFiles).

### Clang Flags

```bash
--target=x86_64-unknown-linux-gnu          # or aarch64-apple-darwin, x86_64-pc-windows-msvc
-DOFFICIAL_BUILD -DEDGE_CHANNEL_STABLE     # DO NOT modify backslashes in -D values!
-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE
../../third_party/llvm-build/Release+Asserts/bin/clang   # relative tool paths
-I../../base -I../../build -Igen                         # include paths
-fmodule-map-file=gen/base/base_module.modulemap         # requires hard links, not symlinks
```

### Python/Mojom Patterns

```bash
python3 gen/mojo/public/tools/bindings/mojom_bindings_generator.py \
  --output_dir=gen --typemap=gen/mojo/public/tools/bindings/blink_bindings.typemap \
  -- third_party/blink/public/mojom/page/page.mojom      # NEVER escape these args

python3 ../../third_party/protobuf/python/google/protobuf/compiler/plugin.py \
  --output=gen/components/autofill/core                   # uses OutputDirectories
```

### Path Translation

RE translates client paths to worker paths:
- `C:\chromium\src\base\file.cc` → `/chromium/src/base/file.cc`
- `..\..\third_party\llvm-build\bin\clang` → `../../third_party/llvm-build/bin/clang`
- **Exception:** `-D` defines preserve backslashes (regex protected)

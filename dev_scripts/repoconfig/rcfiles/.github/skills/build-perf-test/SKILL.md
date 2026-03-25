---
name: build-perf-test
description: >-
  Build performance testing methodology — accurate build time measurement with cache invalidation.
  Use when measuring build times, comparing build performance between commits, testing clang modules impact,
  or doing A/B performance comparisons. Ensures truly uncached builds via source salting.
---

# Build Performance Testing

## Why Salting is Required

Build caches exist at multiple levels:
- **Ninja cache** — tracks file timestamps in `out/<config>/.ninja_deps`
- **Remote Execution (RE) cache** — content-addressed cache shared across all builds
- **ccache/sccache** — local compiler output cache

Simply deleting `out/` only clears the Ninja cache. RE and ccache use **file content hashes**, so they'll still return cached results.

**`salt_chromium_src.py`** appends random comments to widely-included headers, changing their content hash and invalidating ALL cached build artifacts.

## Standard Build Performance Test Procedure

### Single Commit Measurement

```bash
# 1. Setup environment (CRITICAL - must be first!)
set_downstream   # Linux/WSL
# or: Set-Downstream   # Windows PowerShell

# 2. Full sync (ensures clean state)
gclient sync -Df

# 3. Delete output directory
Remove-Item -Recurse -Force out   # or: rm -rf out (Linux)

# 4. Generate build files
autogn

# 5. Build 1: Warmup (may use cached artifacts — DISCARD this time)
$start = Get-Date
autoninja -C out/win_x64_debug_developer_build chrome
$warmup = (Get-Date) - $start
Write-Host "Warmup build: $($warmup.TotalSeconds)s (DISCARDED)"

# 6. Salt source files (invalidates all caches)
python ~/dev_scripts/salt_chromium_src.py

# 7. Delete output directory again
Remove-Item -Recurse -Force out

# 8. Generate build files
autogn

# 9. Build 2: MEASURED BUILD (truly uncached)
$start = Get-Date
autoninja -C out/win_x64_debug_developer_build chrome
$measured = (Get-Date) - $start
Write-Host "Measured build: $($measured.TotalSeconds)s ← USE THIS"
```

### A/B Comparison Between Commits

To compare Commit A (baseline) vs Commit B (test):

```
SETUP (once at start):
  1. set_downstream   # CRITICAL - configures depot_tools for Edge

COMMIT A (baseline):
  1. git checkout <commit_a>
  2. gclient sync -Df
  3. rm -rf out && autogn
  4. Build (warmup, discard)
  5. salt_chromium_src.py
  6. rm -rf out && autogn
  7. Build (measured) → Record time A1
  8. salt_chromium_src.py
  9. rm -rf out && autogn
  10. Build (measured) → Record time A2

COMMIT B (test):
  1. git checkout <commit_b>
  2. gclient sync -Df
  3. salt_chromium_src.py
  4. rm -rf out && autogn
  5. Build (measured) → Record time B1
  6. salt_chromium_src.py
  7. rm -rf out && autogn
  8. Build (measured) → Record time B2

RESULT:
  Baseline = average(A1, A2)
  Test = average(B1, B2)
  Improvement = (Baseline - Test) / Baseline × 100%
```

### Linux Commands

```bash
# Setup (MUST run first!)
set_downstream

# Sync and prepare
gclient sync -Df

# Warmup build
rm -rf out && autogn
time autoninja -C out/linux_x64_debug_developer_build chrome

# Salt and measured build
python3 ~/dev_scripts/salt_chromium_src.py
rm -rf out && autogn
time autoninja -C out/linux_x64_debug_developer_build chrome
```

### Windows Commands (PowerShell)

```powershell
# Setup (MUST run first!)
Set-Downstream

# Sync and prepare
gclient sync -Df

# Warmup build
Remove-Item -Recurse -Force out -ErrorAction SilentlyContinue
autogn
$start = Get-Date; autoninja -C out\win_x64_debug_developer_build chrome; ((Get-Date) - $start).TotalSeconds

# Salt and measured build  
python $env:USERPROFILE\dev_scripts\salt_chromium_src.py
Remove-Item -Recurse -Force out
autogn
$start = Get-Date; autoninja -C out\win_x64_debug_developer_build chrome; ((Get-Date) - $start).TotalSeconds
```

## Critical Rules

| Rule | Reason |
|------|--------|
| **Delete `out/` between EVERY measured build** | Clears ninja cache |
| **Salt BEFORE every measured build** | Invalidates RE/ccache by changing file hashes |
| **Discard warmup build** | First build may use old cached artifacts |
| **Use identical GN args** | Only variable should be the commit/config |
| **Minimum 2 measured runs** | Detect variance, compute meaningful average |
| **Same machine state** | Close other apps, consistent thermal conditions |

## salt_chromium_src.py

Location: `~/dev_scripts/salt_chromium_src.py`

What it does:
```python
# Appends random comments to these files:
FILES = [
    "build/build_config.h",
    "base/base_export.h", 
    "base/memory/raw_ptr.h",
]
# Example: "// testrandomstring-a1b2c3d4e5f6"
```

These headers are included by virtually every compilation unit, so changing them invalidates the entire build cache.

## Automated Scripts

See `C:\dev\documents\scripts\` for automation:
- `run_ab_perf_test.py` — Full A/B comparison workflow
- `measure_build_time.py` — Single build measurement
- `measure_build_resources.py` — CPU/memory monitoring
- `compare_results.py` — Compare JSON results

## Example: Clang Modules Performance Test

Testing the clang modules commits:
- Linux: `aed4e4c074b3d1ed9d9a05e5df14241ffbbde8aa`
- iOS/Mac: `6580e24b11b86633e00d22a73ac9e27ef884f89b`

```bash
# Baseline (parent commit, before modules)
git checkout aed4e4c074b3d1ed9d9a05e5df14241ffbbde8aa^
# ... run measurement procedure ...

# Test (modules enabled)
git checkout aed4e4c074b3d1ed9d9a05e5df14241ffbbde8aa
# ... run measurement procedure ...
```

Expected results based on Chromium data:
- **12.5% build time reduction** on Linux
- **~10% CPU reduction**
- Module cache adds 2-5 GB disk usage

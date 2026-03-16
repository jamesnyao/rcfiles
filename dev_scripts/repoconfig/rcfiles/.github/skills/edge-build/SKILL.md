---
name: edge-build
description: >-
  Edge/Chromium build procedures — full Edge build workflow and build configurations.
  Use when building Edge from source or configuring gn build arguments.
---

# Edge / Chromium Build Procedures

## Full Edge Build

Linux:
```bash
cd edge/src
rm -rf out
gclient sync -Df
autogn
autoninja -C out/linux_x64_debug_developer_build chrome
```

Windows:
```powershell
cd edge\src
Remove-Item -Recurse -Force out
gclient sync -Df
autogn
autoninja -C out\win_x64_debug_developer_build chrome
```

**Note:** This will build on Prod RE by default. To use Preprod RE with no local fallbacks, set the RE Preprod environment variables before running `autoninja` (see the `re-architecture` skill in `es2/RE/.github/skills/`).

`gclient sync -Df` forces a full sync and overwrites local changes. It is required if the source branch changes significantly (ie after running `git pull`).

## Build Configurations

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

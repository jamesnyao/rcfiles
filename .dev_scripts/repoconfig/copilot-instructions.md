# Copilot Instructions

This workspace contains multiple repositories for Microsoft Edge infrastructure and build systems.
Update this file with any relavant information that would help Copilot provide better suggestions.
Review any deletions to this file - unless the information is no longer accurate.

## Critical Rules

**NEVER interrupt a running build unless explicitly asked or there are actual errors.** When a build is in progress and has not generated errors, let it complete. Build interruptions waste significant time and resources.

## Repository Structure

### `/workspace/edge/src` - Chromium Source (chromium.src)
The main Edge/Chromium source code repository.
The base `/workspace/edge` is the Edge enlistment.

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

### `/workspace/es` - Edge Engineering Systems (edgeinternal.es)
Infrastructure, tooling, and Azure resource management.

**Key directories:**
- `RE/` - Remote Execution infrastructure
  - `AzurePipelines/` - Pipeline definitions for RE operations
  - `AzureScripts/` - PowerShell scripts for Azure resource management
  - `AzureTemplates/` - Bicep templates for Azure infrastructure
- `sealion/` - Build pipeline pool management
- `cipd/` - Chrome Infrastructure Package Deployment tools
- `isolateservice/` - Isolate service for build caching

### `/workspace/edge/depot_tools` - Build Tools
Edge fork of Google's depot_tools for Edge development (gclient, gn, ninja wrappers).

### `/workspace/edge2` - Secondary Edge Checkout
Alternative Edge source checkout (same structure as edge/src).

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
set-dev-re; set_remote_only; autoninja -C out/linux_x64_debug_developer_build chrome
```
- `set-dev-re` - Points to the RE Preprod environment
- `set_remote_only` - Prevents local fallbacks from polluting the output and giving false positive build results

**Note:** If testing a preprod build with fallbacks disabled and the build fails purely due to timeouts, restart the build. This is caused by high load and is not indicative of 500 errors.

### Full Uncached Test Build
To perform a full uncached test build (e.g., on Staging), run these steps in order:
```bash
# 1. Salt files to invalidate cache
python3 ~/scripts/salt_chromium_src.py

# 2. Delete out directory
rm -rf out/linux_x64_debug_developer_build

# 3. Sync and regenerate
gclient sync
autogn

# 4. Build with remote-only (use set-dev-re, set-staging-re, or set-prod-re)
set-staging-re; set_remote_only; autoninja -C out/linux_x64_debug_developer_build chrome
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
| RE/Build infrastructure | `es/RE/` |
| iOS entitlements | `edge/src/ios/chrome/*/entitlements/` |
| Build flags | `edge/src/ios/build/chrome_build.gni` |
| Azure resources | `es/RE/AzureTemplates/*.bicep` |

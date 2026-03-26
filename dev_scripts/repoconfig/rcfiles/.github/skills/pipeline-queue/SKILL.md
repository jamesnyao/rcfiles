---
name: pipeline-queue
description: >-
  Queue Azure DevOps pipelines. Use when asked to: trigger a build, queue a
  pipeline, run a try/candidate build, or start a CI pipeline. REQUIRES
  explicit user confirmation before queueing.
---

# Queue Azure DevOps Pipelines

Queue ADO pipelines via REST API. **This is a write operation — always verify parameters and commit before queueing.**

## ⚠️ CRITICAL: Safety Rules

1. **NEVER queue pipelines automatically** — only when EXPLICITLY instructed by the user
2. **ALWAYS verify before queueing:**
   - Pipeline ID and name match user's intent
   - Source branch is correct
   - Source commit (if specified) is correct
   - Template parameters are correct
3. **ALWAYS verify after queueing:**
   - Build name/title reflects expected parameters
   - Source branch and commit match what was requested

## Authentication

Use bearer token authentication via `es delegate` (preferred) or `az account get-access-token`:

```powershell
# Method 1: es delegate (preferred, uses es login credentials)
$result = es delegate --scope "499b84ac-1321-427f-aa17-267ca6975798/.default" --noninteractive 2>&1
$tokenData = $result | ConvertFrom-Json
$token = $tokenData.token

# Method 2: az CLI
$token = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv

# Common headers for all REST calls
$headers = @{ 
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}
```

## Pre-Queue Checklist

### 0. Verify External References (CRITICAL for sealion-dependent builds)

**When queueing builds that use sealion pipeline templates (iOS, Mac, etc.), ALWAYS verify the sealion ref matches your intent:**

```powershell
# Get the commit you're about to queue
$commit = git rev-parse HEAD
$branch = "user/alias/my-branch"

# Check what sealion branch this commit references
$sealionRef = git show ${commit}:anaheim/pipelines/templates/sealion-pipeline-template.yml | Select-String "ref:" | Select-Object -First 1
Write-Host "Sealion ref in commit: $sealionRef"

# If testing a sealion fix, verify the sealion branch has the expected code
# Example: check for a unique string/function in your fix
Set-Location path/to/sealion
$expectedSealionBranch = "user/alias/fix-branch"
$uniqueCode = git show ${expectedSealionBranch}:scripts/srcpub/ios_toolchain_ninja_parser.py | Select-String "your_unique_code_pattern"
if ($uniqueCode) {
    Write-Host "✓ Sealion branch has expected fix"
} else {
    Write-Host "✗ ERROR: Sealion branch missing expected code - DO NOT QUEUE"
    exit 1
}
```

**Common mistakes:**
| Mistake | Result | Fix |
|---------|--------|-----|
| chromium.src branch points to wrong sealion ref | Build uses wrong sealion code | Verify `sealion-pipeline-template.yml` ref before queueing |
| Multiple chromium.src branches point to same sealion | Builds aren't testing different fixes | Check each branch's sealion ref is unique |
| Sealion branch doesn't have your changes | Build tests old/wrong code | Verify unique code exists in sealion branch |

### 1. Get Pipeline Definition

Before queueing, fetch the pipeline definition to understand required parameters:

```powershell
$pipelineId = 50496  # Replace with target pipeline ID
$url = "https://dev.azure.com/microsoft/Edge/_apis/build/definitions/$pipelineId?api-version=7.0"
$def = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

Write-Host "Pipeline: $($def.name)"
Write-Host "Path: $($def.path)"
Write-Host "Repository: $($def.repository.name)"
Write-Host "Default branch: $($def.repository.defaultBranch)"

# List parameters the pipeline accepts
if ($def.process.parameters) {
    Write-Host "`nTemplate parameters:"
    $def.process.parameters | ForEach-Object { 
        Write-Host "  $($_.name): $($_.displayName) (default: $($_.defaultValue))"
    }
}

# List variables
Write-Host "`nVariables:"
$def.variables.PSObject.Properties | ForEach-Object { 
    Write-Host "  $($_.Name) = $($_.Value.value)" 
}
```

### 2. Verify the Commit

If queueing with a specific commit, verify it exists and is correct:

```powershell
$branch = "user/alias/my-branch"
$commit = "abc123def456"

# Get commit details via git (if in local repo)
git log -1 --oneline $commit

# Or via REST API
$repoName = "chromium.src"
$commitUrl = "https://dev.azure.com/microsoft/Edge/_apis/git/repositories/$repoName/commits/$commit?api-version=7.0"
$commitInfo = Invoke-RestMethod -Uri $commitUrl -Headers $headers -Method Get
Write-Host "Commit: $($commitInfo.commitId)"
Write-Host "Author: $($commitInfo.author.name)"
Write-Host "Date: $($commitInfo.author.date)"
Write-Host "Message: $($commitInfo.comment)"

# Verify commit is on the expected branch
$branchUrl = "https://dev.azure.com/microsoft/Edge/_apis/git/repositories/$repoName/refs?filter=heads/$branch&api-version=7.0"
$branchInfo = Invoke-RestMethod -Uri $branchUrl -Headers $headers -Method Get
$branchTip = $branchInfo.value[0].objectId
Write-Host "`nBranch tip: $branchTip"
if ($commit -eq $branchTip) {
    Write-Host "✓ Commit is the branch tip"
} else {
    Write-Host "⚠ Commit is NOT the branch tip — verify this is intentional"
}
```

### 3. Confirm with User

Before queueing, summarize what will be queued and ask for confirmation:

```
About to queue:
  Pipeline: edge-officialcandidate-ios-try (ID: 50496)
  Branch: refs/heads/user/alias/my-branch
  Commit: abc123def456 ("Fix build issue")
  Parameters:
    - BuildConfig: Official
    - SkipTests: false

Proceed? [y/N]
```

## Queue the Build

Use `templateParameters` (NOT `parameters`) to pass pipeline parameters:

```powershell
$body = @{
    definition = @{ id = <DEFINITION_ID> }
    sourceBranch = "refs/heads/<BRANCH_NAME>"  # Must include refs/heads/ prefix
    sourceVersion = "<COMMIT_SHA>"             # Optional: specific commit (omit for branch tip)
    templateParameters = @{
        ParamName1 = "Value1"
        ParamName2 = "Value2"
    }
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds?api-version=7.0" -Headers $headers -Method Post -Body $body
Write-Host "Queued build: $($response.id) - $($response.buildNumber)"
Write-Host "URL: $($response._links.web.href)"
```

### Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Using `parameters` instead of `templateParameters` | Parameters silently ignored | Always use `templateParameters` |
| Missing `refs/heads/` prefix on branch | Build may fail or use wrong branch | Always include full ref path |
| Typo in parameter name | Parameter silently ignored | Copy exact parameter names from definition |

## Post-Queue Verification

**Always verify the queued build matches your intent:**

```powershell
# Fetch the build details
$buildId = $response.id
$build = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/$buildId?api-version=7.0" -Headers $headers

# Verify all the important fields
Write-Host "=== Post-Queue Verification ==="
Write-Host "Build ID: $($build.id)"
Write-Host "Build Number: $($build.buildNumber)"
Write-Host "Definition: $($build.definition.name)"
Write-Host "Source Branch: $($build.sourceBranch)"
Write-Host "Source Version: $($build.sourceVersion)"
Write-Host "Status: $($build.status)"
Write-Host "URL: $($build._links.web.href)"

# Check template parameters were applied
Write-Host "`nTemplate Parameters:"
if ($build.templateParameters) {
    $build.templateParameters.PSObject.Properties | ForEach-Object {
        Write-Host "  $($_.Name) = $($_.Value)"
    }
} else {
    Write-Host "  (none set)"
}

# The build name often encodes parameters (e.g., "MacWorker-Official-..." vs "MacWorker-Preprod-...")
# Verify this matches your intent
Write-Host "`n⚠ CHECK: Does the build name '$($build.buildNumber)' reflect your expected parameters?"
```

### What to Check

| Field | What to Verify |
|-------|---------------|
| `buildNumber` | Often contains parameter values (e.g., `Official` vs `Preprod`) — verify it matches intent |
| `sourceBranch` | Matches the branch you intended |
| `sourceVersion` | Matches the commit SHA (if specified) |
| `templateParameters` | All parameters are present with correct values |
| `definition.name` | Correct pipeline was queued |

## Official-Try/Candidate Pipelines

| Pipeline ID | Name | Purpose |
|-------------|------|---------|
| 50496 | edge-officialcandidate-ios-try | iOS candidate builds |
| 45617 | edge-officialcandidate-linux-try | Linux candidate builds |
| 46358 | edge-officialcandidate-mac-try | macOS candidate builds |
| 46110 | edge-officialcandidate-win-try | Windows candidate builds |
| 44808 | edge-officialcandidate-arm64-try | ARM64 candidate builds |
| 55095 | edge-officialcandidate-android-try | Android candidate builds |

All use repository `chromium.src` with default branch `refs/heads/main`.

## Full Example

Complete workflow for queueing an iOS try build with sealion fix:

```powershell
# 1. Authenticate
$result = es delegate --scope "499b84ac-1321-427f-aa17-267ca6975798/.default" --noninteractive 2>&1
$tokenData = $result | ConvertFrom-Json
$token = $tokenData.token
$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

# 2. Get pipeline info
$pipelineId = 50496
$def = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/definitions/$pipelineId?api-version=7.0" -Headers $headers
Write-Host "Pipeline: $($def.name)"

# 3. Verify commit AND sealion ref
$branch = "user/jamyao/fix-ios-build"
$commit = git rev-parse HEAD
Write-Host "Commit: $commit"

# CRITICAL: Verify sealion ref matches intent
$sealionRef = git show ${commit}:anaheim/pipelines/templates/sealion-pipeline-template.yml | Select-String "ref:" | Select-Object -First 1
Write-Host "Sealion ref: $sealionRef"

# Verify expected sealion branch has unique code for this fix
$expectedSealionBranch = "user/jamyao/my-sealion-fix"
Set-Location C:\dev\sealion
$uniqueCode = git show ${expectedSealionBranch}:scripts/srcpub/ios_toolchain_ninja_parser.py | Select-String "unique_pattern_in_fix"
if (-not $uniqueCode) {
    Write-Host "✗ ERROR: Sealion branch does not contain expected fix code!"
    exit 1
}
Write-Host "✓ Sealion branch verified"
Set-Location C:\dev\edge\src

# 4. Queue build
$body = @{
    definition = @{ id = $pipelineId }
    sourceBranch = "refs/heads/$branch"
    sourceVersion = $commit
    templateParameters = @{
        # Add required parameters here
    }
} | ConvertTo-Json -Depth 5

Write-Host "`nAbout to queue:"
Write-Host "  Pipeline: $($def.name) (ID: $pipelineId)"
Write-Host "  Branch: refs/heads/$branch"
Write-Host "  Commit: $commit"
# Confirm with user before proceeding...

$response = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds?api-version=7.0" -Headers $headers -Method Post -Body $body

# 5. Verify
$build = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/$($response.id)?api-version=7.0" -Headers $headers
Write-Host "`n=== Build Queued ==="
Write-Host "ID: $($build.id)"
Write-Host "Name: $($build.buildNumber)"
Write-Host "Branch: $($build.sourceBranch)"
Write-Host "Commit: $($build.sourceVersion)"
Write-Host "URL: $($build._links.web.href)"
Write-Host "`n✓ Verify the build name and parameters match your intent"
```

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token expired or invalid | Re-run `es login` or `az login`, get fresh token |
| 404 Not Found | Invalid pipeline ID or repo | Verify pipeline ID exists |
| 400 Bad Request | Invalid branch ref or commit | Check `refs/heads/` prefix, verify commit exists |
| Parameters not applied | Used `parameters` instead of `templateParameters` | Use `templateParameters` in request body |

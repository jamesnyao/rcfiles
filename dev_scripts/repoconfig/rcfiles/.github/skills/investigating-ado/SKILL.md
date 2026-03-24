---
name: investigating-ado
description: >-
  Investigate Azure DevOps resources — pull requests, pipeline builds, work
  items, and logs. Use when asked to check build status, find PRs, review
  pipeline failures, or query ADO.
---

# Investigating Azure DevOps

Use the **edge-ado plugin** for ADO operations. It handles authentication automatically via `es login` (preferred) or `az login` — no PAT required.

## Plugin Skills

For most ADO operations, invoke the appropriate plugin skill:

- **`pr` skill** — Find PRs, get details/comments, create/update PRs, add reviewers, set autocomplete, post comments, resolve threads, check policies, queue policy builds
- **`pipeline` skill** — Check build status, investigate pipeline failures, get build logs
- **`workitem` skill** — Create bugs, read/update work items, link work items to PRs

Invoke these skills directly — they contain full usage instructions for all supported operations.

## Queueing Pipelines via REST API

When queueing builds programmatically, use `templateParameters` (not `parameters`) to pass pipeline parameters:

```powershell
$azToken = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
$headers = @{ 
    Authorization = "Bearer $azToken"
    "Content-Type" = "application/json"
}

$body = @{
    definition = @{ id = <DEFINITION_ID> }
    sourceBranch = "refs/heads/<BRANCH_NAME>"
    templateParameters = @{
        ParamName1 = "Value1"
        ParamName2 = "Value2"
    }
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds?api-version=7.0" -Headers $headers -Method Post -Body $body
Write-Host "Build: $($response.id) - $($response.buildNumber)"
```

**Always verify the queued build** — check that the build name/title reflects the expected parameters:

```powershell
# After queueing, verify the build
$build = Invoke-RestMethod -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/$($response.id)?api-version=7.0" -Headers $headers
Write-Host "Build name: $($build.buildNumber)"  # Should reflect your parameters
Write-Host "Template parameters: $($build.templateParameters | ConvertTo-Json)"
Write-Host "Source branch: $($build.sourceBranch)"
```

Common mistakes:
- Using `parameters` instead of `templateParameters` — parameters won't be applied
- The build name often includes parameter values (e.g., `MacWorker-Official-...` vs `MacWorker-Preprod-...`) — verify this matches your intent

## Siso build logs (autoninja failures)

When an `autoninja` build step fails in a pipeline, the detailed build logs are published as a **siso-report** artifact. Use the `pipeline` skill to get the build ID, then download the artifact:

```powershell
# Use az CLI for artifact download (authenticated via az login)
$buildId = "<from pipeline skill>"
$org = "https://dev.azure.com/microsoft"
$project = "Edge"

# List artifacts
az devops invoke --org $org --area build --resource artifacts --route-parameters project=$project buildId=$buildId --api-version 7.1 --query "value[?contains(name,'siso')]"

# Or use the REST API with az CLI auth
$token = az account get-access-token --resource "499b84ac-1321-427f-aa17-267ca6975798" --query accessToken -o tsv
$headers = @{ Authorization = "Bearer $token" }
$artifacts = Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/$buildId/artifacts?api-version=7.1"
$siso = $artifacts.value | Where-Object { $_.name -like '*siso*' }
Invoke-RestMethod -Headers $headers -Uri $siso.resource.downloadUrl -OutFile siso-report.zip
Expand-Archive siso-report.zip -DestinationPath siso-report -Force
Get-ChildItem siso-report -Recurse -Filter *.log | ForEach-Object { Get-Content $_.FullName }
```

For local builds, siso logs are written to `edge/src/out/siso*`.

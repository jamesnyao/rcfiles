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

## Queueing Pipelines

For queueing pipelines, use the **`pipeline-queue` skill**. It includes:
- Pre-queue verification (pipeline definition, commit, parameters)
- Safe queueing workflow with user confirmation
- Post-queue verification checklist
- Common pipeline IDs (official-try/candidate builds)

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

---
name: investigating-ado
description: >-
  Investigate Azure DevOps resources — pull requests, pipeline builds, work
  items, and logs. Use when asked to check build status, find PRs, review
  pipeline failures, or query ADO.
---

# Investigating Azure DevOps

Use the ADO REST API to investigate pull requests, pipeline builds, and other resources.

## Authentication

The ADO PAT is stored at `~/dev_scripts/repoconfig/ado_pat.txt`. Read it before making any API calls:

```powershell
$pat = Get-Content "$HOME/dev_scripts/repoconfig/ado_pat.txt" -Raw | ForEach-Object { $_.Trim() }
$headers = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat")) }
```

If the file is missing or a request returns `401`/`403`, prompt the user to update their PAT with `dev ado set-pat`.

## ADO organization

Most repos are under `https://dev.azure.com/microsoft/Edge`.

Base URL pattern: `https://dev.azure.com/{org}/{project}/_apis/{resource}?api-version=7.1`

## Pull Requests

```powershell
# List PRs for a repository (by repo name)
$repoName = "edgeinternal.es"
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/git/repositories/$repoName/pullrequests?api-version=7.1&searchCriteria.status=active"

# Get a specific PR by ID
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/git/pullrequests/{prId}?api-version=7.1"

# List PR commits
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/git/repositories/$repoName/pullrequests/{prId}/commits?api-version=7.1"

# Get PR threads (comments/reviews)
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/git/repositories/$repoName/pullrequests/{prId}/threads?api-version=7.1"
```

## Pipeline Builds

```powershell
# List recent builds for a pipeline definition
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds?api-version=7.1&definitions={definitionId}&`$top=10"

# Get a specific build
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}?api-version=7.1"

# Get build timeline (stages/jobs/tasks with status)
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}/timeline?api-version=7.1"

# Get build logs (list log entries)
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}/logs?api-version=7.1"

# Get a specific log by ID
Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}/logs/{logId}?api-version=7.1"
```

## Investigating build failures

1. Fetch the build timeline to find failed jobs/tasks.
2. Look for records where `result` is `failed` or `canceled`.
3. Fetch the log for the failed task using its `log.id`.
4. Search the log output for error messages.

```powershell
$timeline = Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}/timeline?api-version=7.1"
$failed = $timeline.records | Where-Object { $_.result -eq 'failed' }
foreach ($task in $failed) {
    if ($task.log) {
        $log = Invoke-RestMethod -Headers $headers -Uri $task.log.url
        Write-Host "=== $($task.name) ===" ; $log | Select-Object -Last 50
    }
}
```

## Siso build logs (autoninja failures)

When an `autoninja` build step fails in a pipeline, the detailed build logs are published as a **siso-report** artifact. Download and unzip it to inspect the actual compiler errors:

```powershell
# List artifacts for a build
$artifacts = Invoke-RestMethod -Headers $headers -Uri "https://dev.azure.com/microsoft/Edge/_apis/build/builds/{buildId}/artifacts?api-version=7.1"

# Find the siso-report artifact
$siso = $artifacts.value | Where-Object { $_.name -like '*siso*' }

# Download and extract
Invoke-RestMethod -Headers $headers -Uri $siso.resource.downloadUrl -OutFile siso-report.zip
Expand-Archive siso-report.zip -DestinationPath siso-report -Force

# Inspect the logs
Get-ChildItem siso-report -Recurse -Filter *.log | ForEach-Object { Get-Content $_.FullName }
```

For local builds, siso logs are written to `edge/src/out/siso*`.

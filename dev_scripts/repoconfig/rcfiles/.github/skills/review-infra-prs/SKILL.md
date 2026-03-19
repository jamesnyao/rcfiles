---
name: review-infra-prs
description: "Review active PRs across Edge infrastructure repos (es, sealion, releasebot). Fetches PRs from ADO, filters by recency/author/draft status, diffs from local git repos, and runs code review. Saves results to a local text file."
---

# Review Infrastructure PRs

Review active Azure DevOps PRs across Edge infrastructure repositories using local git repos for diffs.

## Repos

| Short Name | ADO Repo | Local Path |
|-----------|----------|------------|
| es | edgeinternal.es | `D:\dev\es` (Windows) / `/workspace/es` (Linux) |
| sealion | edgeinternal.es.sealion | `D:\dev\sealion` (Windows) / `/workspace/sealion` (Linux) |
| releasebot | edgeinternal.es.releasebot | `D:\dev\releasebot` (Windows) / `/workspace/releasebot` (Linux) |

## Workflow

### 1. Save repo state
For each repo that has PRs to review:
- Record current branch: `git rev-parse --abbrev-ref HEAD`
- Stash any changes: `git stash`
- Fetch all remote refs: `git fetch origin`

### 2. Find active PRs via ADO REST API

Use the edge-ado plugin scripts or call ADO REST API directly:
```
GET https://dev.azure.com/microsoft/Edge/_apis/git/repositories/{repo}/pullrequests?searchCriteria.status=active&api-version=7.1-preview
```

Auth: Use `_auth.get_token()` from `<edge-ado-plugin>/scripts/_auth.py` or the ADO PAT at `~/dev_scripts/repoconfig/ado_pat.txt`.

### 3. Filter PRs
Apply these filters (configurable by user):
- **Exclude drafts**: Skip PRs where `isDraft == true`
- **Exclude own PRs**: Skip PRs where `createdBy.uniqueName` matches the current user (check `git config user.email` in any tracked repo)
- **Recency**: Only include PRs created/updated within the last 7 days (compare `creationDate` against cutoff)

### 4. Get diffs from local repos (no checkout needed)
For each PR, compute the diff from remote refs without checking out:
```bash
git diff origin/<target_branch>...origin/<source_branch>
```
This is read-only and does not modify the working tree. Save each diff to a temp file.

If the user explicitly asks to run tests or lint locally, then checkout the feature branch:
```bash
git checkout origin/<source_branch>
# run tests/lint
git checkout <original_branch>
```

### 5. Review each diff
Launch code-review agents in parallel for each PR diff. The review prompt should include:
- PR metadata (ID, title, author, branch, URL)
- The diff content
- Instructions to focus on bugs, security issues, logic errors only (no style/formatting nits)

### 6. Compile results
Write all reviews to a single local text file (e.g., `D:\dev\pr_reviews.txt`) with:
- Header with timestamp and filter criteria
- Each PR review with its ADO link
- Summary table of verdicts

### 7. Restore repo state
For each repo:
```bash
git checkout <original_branch>
git stash pop  # only if stash was created
```

### 8. Clean up temp files
Remove diff files and temp JSON files.

## IMPORTANT
- **Do NOT modify feature branches** — diffs are read-only from remote refs
- **Do NOT post comments on the PR** — save reviews locally only
- **Do NOT checkout branches** unless the user explicitly asks for local test/lint runs

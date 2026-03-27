---
name: review-infra-prs
description: "Review active PRs across Edge infrastructure repos (es, sealion, releasebot). Fetches PRs from ADO, filters by recency/author/draft status, diffs from local git repos, and runs code review. Saves results to a local text file."
---

# Review Infrastructure PRs

Review active Azure DevOps PRs across Edge infrastructure repositories using local git repos for diffs.

## Repos

| Short Name | ADO Repo | Local Path |
|-----------|----------|------------|
| es | edgeinternal.es | `./es` |
| sealion | edgeinternal.es.sealion | `./sealion` |
| releasebot | edgeinternal.es.releasebot | `./releasebot` |

## Workflow

### 1. Save repo state
For each repo that has PRs to review:
- Record current branch: `git rev-parse --abbrev-ref HEAD`
- Stash any changes: `git stash`
- Fetch all remote refs: `git fetch origin`

### 2. Find active PRs via ADO REST API

Use the edge-ado plugin to get active PRs for each repo.
Auth: Use `_auth.get_token()` from `<edge-ado-plugin>/scripts/_auth.py`.

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
Launch code-review agents in parallel for each PR diff.

#### Agent prompt requirements
Each review agent prompt MUST include:
- PR metadata (ID, title, pr-description, author, branch, URL)
- The diff file path (agent reads it)
- The local repo path so the agent can read **full source files**, not just the diff
- Instructions per the review quality rules below

#### Review quality rules (include in every agent prompt)

**Verify before flagging.** Do NOT flag an issue based on the diff alone. Before
reporting any finding:
1. **Read the full file(s)** being changed — not just the diff. Check for imports,
   surrounding context, and existing patterns that may address the concern.
2. **Trace runtime paths.** If flagging "X might break Y", verify that the code path
   from X to Y actually executes. Check conditionals, feature flags, config that
   controls whether the code runs.
3. **Check documentation/specs** when the concern is about external API behavior
   (Azure API versions, naming constraints, SDK behavior). If you can't verify,
   say "unverified assumption" rather than stating it as fact.

**Evidence standard.** Every flagged issue must include:
- The **file path and line number** where the problem exists
- A concrete **reproduction scenario** or proof (not "this could theoretically...")
- Confirmation that you **checked the surrounding code** and the issue is real

**What NOT to flag:**
- Speculative issues ("if someone later adds X, this could break")
- Style or formatting preferences
- Issues that require assumptions about external systems you haven't verified
- "Missing" code that may exist in files outside the diff — check first

**Severity calibration:**
- **Critical/High** = will definitely cause a bug, crash, security hole, or data loss
  in production. You must show proof.
- **Medium** = likely causes incorrect behavior in a real scenario. Show the scenario.
- **Low** = code hygiene issue that won't cause user-facing problems.
- If you aren't sure an issue is real after investigating, either downgrade to a
  COMMENT or drop it entirely. Do not guess.

**Verdict guidelines:**
- **APPROVE** = no blocking issues found after thorough investigation
- **COMMENT** = minor observations worth mentioning but not blocking
- **REQUEST_CHANGES** = at least one verified Critical/High issue with evidence

Prefer APPROVE or COMMENT. REQUEST_CHANGES should be reserved for issues you
have confirmed are real. A false REQUEST_CHANGES is worse than a missed Low issue.

### 6. Compare with previous reviews
Before writing results, read the existing `D:\dev\pr_reviews.txt` (if it exists) and identify:
- **Overlapping PRs**: PRs present in both old and new reviews
- **Dropped PRs**: PRs in the old review but not in the new (completed, abandoned, or aged out)
- **New PRs**: PRs in the new review but not in the old

For each overlapping PR:
- Check the last commit date on `origin/<source_branch>` vs the previous review date
- If new commits exist, note "UPDATED since last review" and summarize what changed
- If no new commits, note "No new commits since last review"
- Compare previous and current verdicts; if the verdict changed, document why

### 7. Compile results
Write all reviews to `D:\dev\pr_reviews.txt` (overwrite) with:
- Header with timestamp and filter criteria
- Each PR review with its ADO link
- For overlapping PRs, include a "CHANGE HISTORY" section noting previous verdict, current verdict, and what changed
- Summary table of verdicts
- Order the PRs by severity of issues found, then by recency

### 8. Restore repo state
For each repo:
```bash
git checkout <original_branch>
git stash pop  # only if stash was created
```

### 9. Clean up temp files
Remove diff files and temp JSON files.

## IMPORTANT
- **Do NOT modify feature branches** — diffs are read-only from remote refs
- **Do NOT post comments on the PR** — save reviews locally only
- **Do NOT checkout branches** unless the codebase specifies running tests/linter

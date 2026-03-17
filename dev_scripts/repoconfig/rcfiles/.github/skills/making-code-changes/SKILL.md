---
name: making-code-changes
description: >-
  Guidelines for making code changes. Prefer the smallest diff that solves the
  problem. Use when making code changes, fixing bugs, or refactoring.
---

# Making Code Changes

Always aim for the smallest diff that correctly solves the problem.

## Branching

For new fixes or features, create a feature branch off the latest default branch before making changes:

1. `git fetch origin`
2. `git checkout -b user/<alias>/<short-description> origin/main` (or `origin/master`, whichever is default)
3. Make changes and commit to this branch.

If working on an existing feature branch, make sure it is caught up with the default branch before adding new commits.

## Principles

- **Change only what's necessary.** Don't reformat, rename, or restructure code outside the scope of the fix.
- **Avoid drive-by cleanups.** If you spot unrelated issues, note them — don't bundle them into the same change.
- **Preserve existing style.** Match the surrounding code's formatting, naming, and patterns even if you'd prefer something different.
- **One concern per change.** If a task involves both a bug fix and a refactor, split them into separate commits or PRs.
- **Minimize moved lines.** Reordering functions, imports, or blocks inflates the diff without adding value.
- **Don't add speculative code.** Only add what's needed now — not "just in case" abstractions or unused parameters.

## Code cleanup (apply to new/modified code)

Run the `code-cleanup` skill on the code you are adding or modifying before committing.

## When reviewing your own diff

Before committing, review the diff and ask:

1. Is every changed line required to solve the problem?
2. Could I achieve the same result by changing fewer files or fewer lines?
3. Did I accidentally include whitespace, formatting, or import-order changes?

If the answer to 1 or 2 is no, trim the diff. If 3 is yes, revert the noise.

## Pushing

Never use `git push --force`. If the remote has diverged, rebase or merge locally and push normally.

## Pull Requests

After pushing, create a PR via the ADO REST API. Target the default branch from the feature branch. Write a description proportional to the change — only include what the change does and why. A one-line fix needs a one-line description, not a paragraph. Avoid being verbose. Include links to relevant context (e.g. the failing build or issue that motivated the change) and paste the key error snippet that shows exactly why the fix is needed. Use the `investigating-ado` skill for API patterns.

If a PR already exists for the branch, review the title and description after pushing. Fix any info that is now inaccurate or misleading given the latest changes.

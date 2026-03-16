---
name: making-code-changes
description: >-
  Guidelines for making code changes. Prefer the smallest diff that solves the
  problem. Use when making code changes, fixing bugs, or refactoring.
---

# Making Code Changes

Always aim for the smallest diff that correctly solves the problem.

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

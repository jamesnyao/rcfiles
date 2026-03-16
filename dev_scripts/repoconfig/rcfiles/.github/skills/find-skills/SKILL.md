---
name: find-skills
description: >-
  Discover Copilot skills nested in subdirectories across the workspace.
  Use when a task might benefit from a specialized skill you don't currently
  have loaded, or when the user asks about available skills.
---

# Find Skills

This workspace contains Copilot skills at the top level (`.github/skills/`) **and** inside nested repositories. Only top-level skills are loaded automatically — nested skills must be invoked by name after discovery.

## How to discover nested skills

Run this from the workspace root to list every skill with its name and description:

```powershell
Get-ChildItem -Path . -Recurse -Filter SKILL.md |
  Where-Object { $_.FullName -notlike '*node_modules*' -and $_.FullName -notlike '*third_party*' } |
  ForEach-Object {
    $rel = $_.FullName.Substring((Get-Location).Path.Length + 1)
    $head = Get-Content $_.FullName -TotalCount 20 -Raw
    if ($head -match '(?s)name:\s*(.+?)[\r\n]') { $name = $Matches[1].Trim() } else { $name = '?' }
    if ($head -match '(?s)description:\s*[>|-]?\s*(.+?)(?=\n[a-z]|\n---|\z)') { $desc = $Matches[1].Trim() -replace '\s+', ' ' } else { $desc = '' }
    [PSCustomObject]@{ Name = $name; Path = $rel; Description = $desc }
  } | Format-Table -Wrap -AutoSize
```

## Known skill locations

| Repository / Path | Skills directory |
|---|---|
| _(workspace root)_ | `.github/skills/` |
| `edge/src` | `edge/src/.github/skills/` |
| `es/integration_pump` | `es/integration_pump/.github/skills/` |
| `es2/integration_pump` | `es2/integration_pump/.github/skills/` |
| `es/docs/team/bdw` | `es/docs/team/bdw/.github/skills/` |

## Workflow

1. Run the discovery command (or grep for `SKILL.md`) to get the full list.
2. Read the relevant `SKILL.md` to understand what it does.
3. Invoke the skill by name if it matches the current task.

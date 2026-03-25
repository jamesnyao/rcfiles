---
name: creating-skills
description: Guidelines for creating new Copilot skills in the workspace root. Use when creating or organizing skills.
---

# Creating New Skills

When creating new Copilot skills, always place them in the workspace root:

```
C:\dev\.github\skills/<skill-name>/SKILL.md     # Windows
/workspace/.github/skills/<skill-name>/SKILL.md  # Linux
```

## Why Not in Individual Repos?

- Skills in `C:\dev\.github\skills/` are synced via `dev repo sync` to rcfiles
- This makes them available across all machines automatically
- Skills in individual repos (e.g., `edge-agents/.github/skills/`) are repo-specific and won't sync

## Creating a New Skill

1. Create the directory: `mkdir -p C:\dev\.github\skills\<skill-name>`
2. Create `SKILL.md` with the skill content
3. Run `dev repo sync` to push to rcfiles

## Skill File Format

```markdown
# Skill Title

Brief description of when to use this skill.

## Section 1
Content...

## Section 2
Content...
```

The skill will be automatically discovered by the `find-skills` skill.

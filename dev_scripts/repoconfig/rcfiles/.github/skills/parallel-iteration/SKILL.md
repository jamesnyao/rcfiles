---
name: parallel-iteration
description: Parallel agent strategy for long-running validation tasks (1hr+ pipelines). Use when a code change requires expensive validation, A/B testing across approaches, or when you want to explore multiple solutions simultaneously and converge on the best one.
---

# Parallel Iteration for Long-Running Validation

Use this strategy when validating a code change requires an expensive feedback loop — builds, pipelines, or tests that take **1 hour or more**. Instead of trying one approach, waiting, failing, and retrying serially, launch **three parallel agents** that each pursue a distinct approach and converge on the validated solution.

## When to Use

- Pipeline or build validation takes 1hr+
- Multiple viable approaches exist and it's unclear which will work
- Cost of a failed attempt is high (wasted time, not resources)
- You want to maximize the chance of a first-pass success

## Strategy Overview

```
┌─────────────────────────────────────────────────┐
│              COORDINATOR (you)                  │
│  1. Analyze problem                             │
│  2. Identify 3 distinct approaches              │
│  3. Create knowledge file (REQUIRED)            │
│  4. Launch 3 agents in parallel                 │
│  5. Monitor, collect results, pick winner        │
└────────┬──────────────┬──────────────┬──────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
    │ Agent A │   │  Agent B  │  │ Agent C │
    │ Approach│   │  Approach │  │ Approach│
    │   #1    │   │    #2     │  │   #3    │
    └────┬────┘   └─────┬─────┘  └────┬────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
              Validated Solution
```

## Step-by-Step Process

### 1. Analyze and Decompose

Before launching agents, understand the problem space:

- What exactly needs to change?
- What are the validation criteria? (build passes, tests green, pipeline succeeds)
- What are the plausible approaches?

### 2. Create the Knowledge File (REQUIRED)

**You MUST create a knowledge file before launching agents.** This file lives in the session workspace and serves as both a shared context document and a living plan.

Save to: `~/.copilot/session-state/<session-id>/files/parallel-plan.md`

The file must follow this exact structure:

```markdown
# Parallel Iteration Plan

## Problem
< 2-3 sentences. What broke or needs to change. >

## Goal
< 1 sentence. The single measurable outcome. >

## Validation
< How to confirm success. Pipeline name, test command, build target. >

## Approaches

### A: <Name>
- **Idea:** < 1 sentence >
- **Key files:** < list >
- **Risk:** < 1 sentence >
- **Status:** 🔲 not started

### B: <Name>
- **Idea:** < 1 sentence >
- **Key files:** < list >
- **Risk:** < 1 sentence >
- **Status:** 🔲 not started

### C: <Name>
- **Idea:** < 1 sentence >
- **Key files:** < list >
- **Risk:** < 1 sentence >
- **Status:** 🔲 not started

## Decisions Log
| # | Decision | Why |
|---|----------|-----|

## Result
< Filled in after convergence. Which approach won and why. >
```

**Rules for the knowledge file:**
- Keep it **scannable** — bullet points, tables, short sentences
- No paragraphs longer than 2 lines
- Update status emoji as work progresses: 🔲 → 🔄 → ✅ / ❌
- Every agent reads this file at start and can reference it if lost

### 3. Launch Three Agents

Use `mode: "background"` so all three run simultaneously. Each agent prompt must include:

1. **The full knowledge file content** (copy-paste it into the prompt)
2. **Which approach (A/B/C) this agent owns**
3. **Explicit instruction not to use the other approaches**
4. **The validation step to run after making changes**

Template for agent prompts:

```
You are Agent [A/B/C] in a parallel iteration. Three agents are working
on the same problem simultaneously, each with a different approach.

YOUR APPROACH: [Name] — [1-sentence description]
DO NOT USE these approaches (other agents own them):
- [Other approach 1]
- [Other approach 2]

PROBLEM: [from knowledge file]
GOAL: [from knowledge file]

STEPS:
1. Make the code changes for your approach
2. Run: [validation command]
3. Report: what you changed, whether validation passed, any issues

KEY FILES: [list from knowledge file]

[Paste full knowledge file here for reference]
```

**Agent configuration:**
- Use `agent_type: "general-purpose"` for complex code changes
- Use `agent_type: "task"` if the change is mechanical and validation is the bottleneck
- All three agents MUST have equal detail and effort in their prompts

### 4. Monitor and Converge

While agents run:
- You'll be notified as each completes
- Read results with `read_agent`
- Update the knowledge file status for each approach

After all complete (or first success):
- If one agent's approach passed validation → adopt it, update knowledge file `## Result`
- If multiple passed → pick the cleanest diff, note in `## Decisions Log`
- If none passed → analyze failures, create a new knowledge file for round 2

### 5. Update Knowledge File with Result

```markdown
## Result
**Winner: Approach B** — [Name]
- Passed validation: [pipeline link / test output]
- Changes: [list of files modified]
- Why others failed:
  - A: [reason]
  - C: [reason]
```

## Example: RE Build Fix

```markdown
# Parallel Iteration Plan

## Problem
Cross-compilation builds fail with "Could not find output files" for
Windows-target actions on Linux RE workers after updating path handling.

## Goal
RE Preprod build completes with 0 errors for win_x64_debug target.

## Validation
`Set-Downstream; Set-DevRE; Set-RemoteOnly; autoninja -C out\win_x64_debug_developer_build chrome`

## Approaches

### A: Fix PathHelper translation
- **Idea:** The new regex in TranslateWindowsPathToUnixPath misses UNC paths
- **Key files:** PathHelper.cs, ExecuteStage.cs
- **Risk:** May break Linux-native builds
- **Status:** 🔄 in progress

### B: Fix output file collection
- **Idea:** OutputFileCollector uses wrong separator when TargetOS=Windows
- **Key files:** TelemetryOutputFileCollector.cs, ExecuteStage.cs
- **Risk:** Might mask the real path issue
- **Status:** 🔄 in progress

### C: Fix BuildArguments backslash logic
- **Idea:** The -D define regex doesn't cover /FI flags, causing path corruption
- **Key files:** ExecuteStageUnix.cs, ExecuteStageTests.cs
- **Risk:** Narrow fix, may not cover all cases
- **Status:** 🔄 in progress
```

## Anti-Patterns

| ❌ Don't | ✅ Do |
|----------|-------|
| Launch agents without a knowledge file | Always create the plan first |
| Give one agent more detail than others | Equal effort in all three prompts |
| Let agents pick overlapping approaches | Explicitly assign and exclude |
| Skip the validation step in agent prompts | Every agent must validate its own change |
| Forget to update the knowledge file | Update status and result after completion |
| Run more than 3 agents | 3 is the sweet spot — more adds coordination overhead |
| Use this for tasks with <30min validation | Serial iteration is fine for fast feedback loops |

## Checklist

Before launching parallel iteration, confirm:

- [ ] Knowledge file created in session workspace
- [ ] Three distinct approaches identified
- [ ] Each approach has: idea, key files, risk
- [ ] Validation command/criteria documented
- [ ] Agent prompts include full knowledge file
- [ ] Each agent knows which approaches are off-limits

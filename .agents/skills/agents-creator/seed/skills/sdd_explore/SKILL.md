---
name: sdd_explore
description: Pre-plan exploration for large, legacy, or ambiguous features. Persists explore.md under ai-system/changes/<feature>/ with touched areas, key files, risks, and open questions. No implementation and no task list — discovery only. Use before sdd_design when scope is unclear or the feature touches legacy code.
---

# SDD Explore — Discovery Phase

## When to Use

Run this skill before `sdd_design` when:
- The feature is large or touches many modules
- The codebase area is legacy or unfamiliar
- The scope is ambiguous — you are not sure what will be affected
- A previous attempt produced unexpected side effects

Do NOT use this skill for: bug fixes, small UI changes, doc-only changes, or config updates.

## What This Skill Does NOT Do

- Does NOT produce a task list
- Does NOT write any implementation code
- Does NOT make decisions — it surfaces information for decisions to be made in sdd_design

## Instructions

1. Read the feature request or ticket description carefully.
2. Search the codebase for all files related to the feature:
   - Files that will likely be created
   - Files that will likely be modified
   - Files that must NOT be touched (shared utilities, core modules)
3. Identify cross-cutting concerns: DI, routing, i18n, state management, shared models.
4. Identify risks: shared state, breaking changes, performance impact, circular dependencies.
5. List open questions that must be answered before design begins.
6. Write the output to `ai-system/changes/<feature>/explore.md`.

## Output Format

Write `ai-system/changes/<feature>/explore.md`:

```
# Explore: <feature-name>

**Date:** <YYYY-MM-DD>
**Status:** Draft

## Summary
One paragraph describing what this feature does and why it's complex enough to require exploration.

## Touched Areas

| Area | Files | Type of Change |
|------|-------|---------------|
| <layer/module> | <file paths> | Create / Modify / Delete |

## Key Files

List the most important files to understand before designing this feature:
- `<path>` — <why it matters>

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <risk> | High/Med/Low | High/Med/Low | <approach> |

## Open Questions

Questions that must be answered before sdd_design begins:
1. <question>
2. <question>

## Out of Scope

Explicitly list what this feature does NOT cover.
```

## Enforcement Rules

- Never write implementation code during this phase.
- Never produce a task list — that is sdd_design's job.
- If you cannot find enough information in the codebase, say so explicitly in Open Questions.
- If scope is too large for one feature, recommend splitting it and explain how.

---
name: sdd_design
description: Design phase — persists design.md for a feature under ai-system/changes/<feature>/. Produces architecture decision records (ADRs), data flow diagram, complete file-change table, testing strategy, and agent execution order. Use after explore.md exists (or directly for clear-scope features), before any implementation. Never writes implementation code.
---

# SDD Design — Design Phase

## When to Use

Run this skill after `sdd_explore` (or directly for features with clear scope):
- Before writing any implementation code for a non-trivial feature
- When you need to document architecture decisions for team review
- When multiple implementation approaches exist and one must be chosen

Do NOT use this skill for: bug fixes, small UI changes, config-only changes.

## What This Skill Does NOT Do

- Does NOT write implementation code
- Does NOT execute tasks — it plans them
- Does NOT proceed to implementation automatically

## Instructions

1. Read `ai-system/changes/<feature>/explore.md` if it exists.
2. Read relevant architecture context from `ai-system/context/architecture.md`.
3. Design the solution — consider at least two approaches, choose one, document the tradeoff.
4. Produce the complete file-change table (every file that will be created or modified).
5. Define the testing strategy.
6. Define the agent execution order for implementation waves.
7. Write the output to `ai-system/changes/<feature>/design.md`.
8. **Wait for user approval before any implementation begins.**

## Output Format

Write `ai-system/changes/<feature>/design.md`:

```
# Design: <feature-name>

**Date:** <YYYY-MM-DD>
**Status:** Draft → Approved → Implemented

## Context
Brief description of what is being built and why.

## Architecture Decision Records (ADRs)

### ADR-001: <Decision Title>
- **Decision:** <what was decided>
- **Alternatives considered:** <other options>
- **Rationale:** <why this option was chosen>
- **Consequences:** <tradeoffs accepted>

## Data Flow

[Describe or diagram the data flow from input to output]

## File-Change Table

| File | Action | Layer | Notes |
|------|--------|-------|-------|
| <path> | Create / Modify / Delete | <layer> | <notes> |

## Testing Strategy

| Layer | Test type | Tools | Coverage target |
|-------|-----------|-------|----------------|
| <layer> | Unit / Integration / E2E | <tools> | <% > |

## Agent Execution Order

1. <agent-name> — <what it handles>
2. <agent-name> — <what it handles>
...

## Open Questions (if any)

Questions that arose during design and need team input before implementation.
```

## Enforcement Rules

- Never write implementation code.
- Never proceed to implementation without explicit user approval of this document.
- If the file-change table has more than 20 files, recommend splitting the feature.
- Every ADR must include at least one alternative considered.

---
name: sdd_verify
description: Post-implementation validation gate. Checks implemented files against design.md, applies heuristic architecture rules, and runs scoped tests. Writes ai-system/changes/<feature>/verify-report.md with CRITICAL, WARNING, and SUGGESTION items. Use after all implementation waves are complete, before opening a PR. Fix all CRITICAL items before pushing.
---

# SDD Verify — Validation Phase

## When to Use

Run this skill after all implementation waves are complete and before opening a PR:
- When you have finished implementing a feature
- When you want to confirm compliance with the project's architecture rules
- When you want a final checklist before code review

## Instructions

1. Read `ai-system/changes/<feature>/design.md` to get the planned file-change table.
2. For each file in the table:
   - Verify the file exists
   - Verify the layer placement is correct (no cross-layer violations)
   - Verify naming conventions follow coding-standards.md
3. Run scoped tests for the feature and report results.
4. Apply architecture heuristics (see rules below).
5. Write the output to `ai-system/changes/<feature>/verify-report.md`.

## Architecture Heuristics (always check)

- No business logic in the presentation layer
- No direct data source calls from use cases (must go through repository)
- No hardcoded strings visible to users (must be i18n keys)
- No circular dependencies between layers
- All public interfaces have the correct abstract type in DI registration
- No file exceeds the project's line limit (from coding-standards.md)
- All new Freezed/generated models have been regenerated (if applicable)

## Output Format

Write `ai-system/changes/<feature>/verify-report.md`:

```
# Verify Report: <feature-name>

**Date:** <YYYY-MM-DD>
**Status:** PASS / FAIL (CRITICAL items present)

## Test Results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| <suite> | N | N | N |

## File Coverage

| Planned File | Found | Correct Layer | Naming OK |
|-------------|-------|--------------|-----------|
| <path> | ✅/❌ | ✅/❌ | ✅/❌ |

## Issues

### CRITICAL (must fix before PR)
- [ ] <issue> — <file> — <what to fix>

### WARNING (should fix, not blocking)
- [ ] <issue> — <file> — <recommendation>

### SUGGESTION (optional improvement)
- [ ] <issue> — <file> — <recommendation>

## Summary

Overall assessment and next steps.
```

## Enforcement Rules

- A verify-report.md with any CRITICAL item means the feature is NOT ready for PR.
- Do not mark a CRITICAL as WARNING to make the report look better.
- If tests fail, the report status is FAIL regardless of other checks.
- If design.md does not exist, write a WARNING stating that design documentation is missing.

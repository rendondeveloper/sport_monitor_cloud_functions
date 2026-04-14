---
name: skill_registry
description: Scans ai-system/skills/ for all SKILL.md files and regenerates ai-system/skill-registry.md — the canonical catalog of skill names, paths, and descriptions. Use after adding, removing, or renaming any skill. Architects and orchestrators read the registry once per session to know what tools are available.
---

# Skill Registry — Catalog Regenerator

## When to Use

Run this skill whenever:
- A new skill is added to `ai-system/skills/`
- A skill is renamed or removed
- The `skill-registry.md` looks out of date
- An orchestrator agent needs to refresh its knowledge of available tools

## Instructions

1. Scan all directories under `ai-system/skills/`.
2. For each directory, read the `SKILL.md` file's frontmatter (`name` and `description` fields).
3. Sort skills alphabetically by name.
4. Write the complete regenerated table to `ai-system/skill-registry.md`.

## Output Format

Write `ai-system/skill-registry.md`:

```
# Skill Registry

**Generated:** <YYYY-MM-DD>
Regenerate with `/skill_registry` after adding, removing, or renaming skills.

| Skill name | Path | Description |
|------------|------|-------------|
| `<name>` | `ai-system/skills/<name>/SKILL.md` | <description from frontmatter> |
...

## How to Invoke

Use `/<skill-name>` in Claude Code or Cursor to activate a skill.
```

## Enforcement Rules

- Include every SKILL.md found — do not filter or omit any.
- If a SKILL.md has no frontmatter or is missing `name`/`description`, log a WARNING in the registry but still include the entry with `⚠️ MISSING FRONTMATTER`.
- Never edit individual SKILL.md files during this operation — read only.
- The registry is generated output — never edit it by hand; always regenerate with this skill.

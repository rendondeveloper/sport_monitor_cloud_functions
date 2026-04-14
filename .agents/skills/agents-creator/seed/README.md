# Seed bundle — protocol for `agents-creator`

These files are **canonical templates**. Phase 3 copies them into the project’s **`<config_dir>`** (any repo-relative path the user chose, e.g. `ai-system/` or `packages/my-app/ai-system/`).

## Resolve paths

- **`SKILL_ROOT`**: directory that contains this skill’s `SKILL.md` (parent of `seed/`).
- **`<config_dir>`**: AI config root in the **target repo** (from `.setup-config.yaml` / Phase 0).

## SDD skills (`seed/skills/**/SKILL.md`)

1. Copy each file to `<config_dir>/skills/<name>/SKILL.md` (create directories).
2. In every copied `SKILL.md`, replace the path prefix **`ai-system/`** with **`<config_dir>/`** (use the actual repo-relative string, e.g. `packages/foo/ai-system/`). Apply to descriptions and body paths so SDD outputs point at the real config tree.
3. Optionally adjust wording for stack-specific hints after the replace.

## Agents (`seed/agents/*.md`)

1. Copy to `<config_dir>/agents/architect.md`, `docs-agent.md`, `testing-agent.md`.
2. Replace `<Project Name>`, `<config_dir>`, and fill tables per Phase 3.5–3.7 (skills list, coordination order, test commands).

## Snippets (not under `<config_dir>`)

| File | Destination |
|------|-------------|
| `snippets/claude-architect-always.md` | Merge into **project root** `CLAUDE.md` (Phase 3.9). |
| `snippets/structure_project.mdc` | Merge into **`.cursor/rules/structure_project.mdc`**. |

Replace `<config_dir>` and `<Project Name>` in the snippet content when merging.

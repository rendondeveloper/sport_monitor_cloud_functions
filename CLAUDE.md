# Sport Monitor Cloud Functions

## Architect mode (always — Claude Code / CLI / plugin)

Apply the **same** orchestration as `ai-system/agents/architect.md` in **every** conversation in this repository, including greetings. You do not need the user to invoke a separate "Architect" agent.

### Canonical source of truth

1. Read and follow **`ai-system/agents/architect.md`** when it exists.
2. At session start (before substantive code work), read when present: **`ai-system/skill-registry.md`** and **`ai-system/context/architecture.md`**.

### Greetings

For hi/hello only: **2–5 lines** as Architect; no full Action plan table until there is a concrete task.

### Trigger word (Architect wake word)

Read `trigger_word` from `ai-system/.setup-config.yaml` at session start.
If the user's message contains `work backend`: activate Architect mode immediately —
produce a full **Action plan** for the task described in the message, then wait for
`ok` before executing or delegating. No side effects until confirmed.

If `ai-system/.setup-config.yaml` does not exist yet, fall back to **"work with"** as the wake word.

### Before edits or delegation

Full **Action plan** (Objective, Steps, Delegation, Scope, Risks/unknowns) **before** writes, side effects, or implementation delegation; user approval for non-trivial scope unless already approved. Read-only exploration alone is exempt from the full table.

**Confirmation word bypass:** Read `confirmation_word` from `ai-system/.setup-config.yaml` (default: `ok`). If the user's message includes the confirmation word, skip the Action plan and user approval gate — proceed directly to execution or delegation for that turn only.

### Architect must not implement product code

- **Do not** edit application or library source (e.g. under `functions/`); **delegate** to specialist agents. You may update **orchestration artifacts** under `ai-system/` such as `changes/<feature>/handoff.md` (and optional `progress.md`) as defined in `agents/architect.md`.
- If a delegated wave is **incomplete** or fails its exit criteria: **send the same agent back** with a fix list — **do not** finish the wave yourself or advance to the next agent on partial output. Use only **finalized** handoffs when sequencing.
- For **active SDD features**, read `ai-system/changes/<feature>/handoff.md` early in the session (after `design.md` when it exists) so continuity works across **Cursor, Claude Code, and other clients** without chat history.

### Context (project)

@ai-system/context/workflow.md
@ai-system/context/architecture.md
@ai-system/context/coding-standards.md
@ai-system/context/project-structure.md

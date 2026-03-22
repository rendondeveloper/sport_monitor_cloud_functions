# Skill: /skill_registry

**Categoria**: Proceso
**Output**: `ai-system/skill-registry.md`

---

## Cuando usar

- Cuando se añade un skill nuevo al sistema
- Cuando se añade un agente nuevo
- Cuando cambia el propósito o la responsabilidad de un skill existente
- Revisión periódica de estado del ai-system

---

## Proceso

1. Leer `ai-system/manifest.yaml` — fuente de verdad de skills y agentes registrados
2. Leer cada `ai-system/skills/*/SKILL.md` para verificar que el archivo existe
3. Leer cada `ai-system/agents/*.md` para verificar que el archivo existe
4. Actualizar `ai-system/skill-registry.md` con el estado actual

---

## Output format

Actualizar `ai-system/skill-registry.md`:

```markdown
# Skill Registry — Sport Monitor Cloud Functions

Indice completo de skills y agentes. Generado por `/skill_registry`.
Ultima actualizacion: YYYY-MM-DD

---

## Agentes

| Nombre | Model | Path | Responsabilidad | Archivo existe |
|--------|-------|------|-----------------|----------------|
| architect | opus | agents/architect.md | Coordinador | Si |
| functions-cross | haiku | agents/functions-cross.md | main.py, modelos, utils | Si |
| functions-endpoint | haiku | agents/functions-endpoint.md | Endpoints HTTP | Si |
| functions-test | sonnet | agents/functions-test.md | pytest tests | Si |
| functions-docs | opus | agents/functions-docs.md | README módulos | Si |

---

## Skills por categoria

### Workflow

| Skill | Path | Archivo existe | Ultima modificacion |
|-------|------|----------------|---------------------|
| /plan | skills/plan/SKILL.md | Si | 2026-03-21 |
| /sdd_explore | skills/sdd_explore/SKILL.md | Si | 2026-03-21 |
| /sdd_design | skills/sdd_design/SKILL.md | Si | 2026-03-21 |
| /sdd_verify | skills/sdd_verify/SKILL.md | Si | 2026-03-21 |

### Código

| Skill | Path | Archivo existe | Ultima modificacion |
|-------|------|----------------|---------------------|
| /new-function | skills/new-function/SKILL.md | Si | 2026-03-21 |
| /add-model | skills/add-model/SKILL.md | Si | 2026-03-21 |
| /add-util | skills/add-util/SKILL.md | Si | 2026-03-21 |
| /add-firestore-query | skills/add-firestore-query/SKILL.md | Si | 2026-03-21 |

### Testing

| Skill | Path | Archivo existe | Ultima modificacion |
|-------|------|----------------|---------------------|
| /add-test | skills/add-test/SKILL.md | Si | 2026-03-21 |
| /qa-ready | skills/qa-ready/SKILL.md | Si | 2026-03-21 |

### Proceso

| Skill | Path | Archivo existe | Ultima modificacion |
|-------|------|----------------|---------------------|
| /push | skills/push/SKILL.md | Si | 2026-03-21 |
| /update-readme | skills/update-readme/SKILL.md | Si | 2026-03-21 |
| /skill_registry | skills/skill_registry/SKILL.md | Si | 2026-03-21 |

---

## Historial de cambios

### 2026-03-21
- Creación inicial del ai-system con 13 skills y 5 agentes
```

---

## Cómo añadir un skill nuevo

1. Crear `ai-system/skills/<nombre>/SKILL.md` con el contenido del skill
2. Añadir entrada en `ai-system/manifest.yaml` bajo `skills:`
3. Ejecutar `/skill_registry` para actualizar `skill-registry.md`
4. Commit: `docs(ai-system): add <nombre> skill to registry`

## Cómo añadir un agente nuevo

1. Crear `ai-system/agents/<nombre>.md` con el contenido del agente
2. Añadir entrada en `ai-system/manifest.yaml` bajo `agents:`
3. Ejecutar `/skill_registry` para actualizar `skill-registry.md`
4. Commit: `docs(ai-system): add <nombre> agent`

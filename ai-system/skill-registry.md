# Skill Registry — Sport Monitor Cloud Functions

**Generated:** 2026-04-14
Regenerate with `/skill_registry` after adding, removing, or renaming skills.

---

## Agentes

| Nombre | Model | Path | Responsabilidad |
|--------|-------|------|-----------------|
| architect | opus | agents/architect.md | Main orchestrator — validates plans, coordinates agents, enforces architecture |
| docs-agent | opus | agents/docs-agent.md | Senior technical writer — cross-cutting documentation |
| testing-agent | opus | agents/testing-agent.md | Senior QA engineer — deep validation and audit |
| functions-cross | haiku | agents/functions-cross.md | Registro main.py, FirestoreCollections, modelos, utils |
| functions-endpoint | haiku | agents/functions-endpoint.md | Implementación endpoints HTTP con template obligatorio |
| functions-test | sonnet | agents/functions-test.md | pytest — AAA, mocks, cobertura >= 90% |
| functions-docs | opus | agents/functions-docs.md | README por módulo |

---

## Skills por categoria

### Workflow — planificación y verificación

| Skill | Trigger | Path | Output |
|-------|---------|------|--------|
| /plan | Antes de cualquier implementación | skills/plan/SKILL.md | Plan estructurado con waves |
| /sdd_explore | Módulo existente con lógica compleja | skills/sdd_explore/SKILL.md | changes/<module>/explore.md |
| /sdd_design | Diseño de contratos HTTP | skills/sdd_design/SKILL.md | changes/<module>/design.md |
| /sdd_verify | Post-implementación, pre-deploy | skills/sdd_verify/SKILL.md | Checklist completado |

### Código — implementación

| Skill | Trigger | Path | Output |
|-------|---------|------|--------|
| /new-function | Crear endpoint HTTP nuevo | skills/new-function/SKILL.md | Archivo Python + registro main.py |
| /add-model | Modelo Firestore nuevo | skills/add-model/SKILL.md | models/<nombre>.py |
| /add-util | Helper reutilizable nuevo | skills/add-util/SKILL.md | utils/<nombre>.py |
| /add-firestore-query | Query Firestore compleja | skills/add-firestore-query/SKILL.md | Función auxiliar en el módulo |

### Testing

| Skill | Trigger | Path | Output |
|-------|---------|------|--------|
| /add-test | Función nueva o modificada | skills/add-test/SKILL.md | tests/test_<module>_<function>.py |
| /qa-ready | Pre-deploy de cambio grande | skills/qa-ready/SKILL.md | changes/<module>/verify-report.md |

### Proceso — documentación y deploy

| Skill | Trigger | Path | Output |
|-------|---------|------|--------|
| /update-readme | Endpoint nuevo o modificado | skills/update-readme/SKILL.md | functions/<module>/README.md |
| /deploy | Post-push, antes de producción | skills/deploy/SKILL.md | Deploy report |
| /push | Cambio listo para commit | skills/push/SKILL.md | Commit con Conventional Commits |
| /skill_registry | Skill nuevo agregado | skills/skill_registry/SKILL.md | ai-system/skill-registry.md |

---

## How to Invoke

Use `/<skill-name>` in Claude Code or Cursor to activate a skill.

---

## Wave execution

```
Wave 1 (parallel)
  ├── functions-cross  →  main.py + FirestoreCollections + modelos + utils
  └── functions-endpoint  →  handler HTTP con template obligatorio

Wave 2 (sequential)
  └── functions-test  →  tests/test_<module>_<function>.py

Wave 3 (sequential, OBLIGATORIO)
  └── functions-docs  →  functions/<module>/README.md
```

---

## Reglas que aplican a TODOS los skills

1. Template obligatorio: `validate_request` + `verify_bearer_token` + early return
2. Respuestas exitosas: JSON directo — sin wrappers `success`, `data`, `message`
3. Errores: código HTTP vacío — sin JSON en body de error
4. CORS headers en TODAS las respuestas (éxito y error)
5. `FirestoreCollections` para todos los nombres de colecciones
6. `FirestoreHelper` para todo CRUD — no `firestore.client()` directo

---

*Ultima actualización: 2026-04-14*

# Skill: /push

**Categoria**: Proceso
**Output**: Commit en git con Conventional Commits

---

## Cuando usar

Cuando el cambio está completo:
- Wave 1 (implementación) completo
- Wave 2 (tests) pasando con >= 90% cobertura
- Wave 3 (docs) completo
- /sdd_verify completado

---

## Conventional Commits para este proyecto

Formato: `<type>(<scope>): <descripción en imperativo>`

### Types

| Type | Cuando usar |
|------|-------------|
| `feat` | Nueva Cloud Function o nueva capacidad en una función existente |
| `fix` | Corrección de bug en función existente |
| `test` | Tests nuevos o corrección de tests sin cambiar código fuente |
| `docs` | Solo cambios en README o documentación |
| `refactor` | Refactor interno sin cambiar comportamiento observable |
| `chore` | Cambios en config, requirements, deploy scripts |
| `perf` | Mejora de rendimiento (reducción de queries, caching) |

### Scopes — módulos del proyecto

| Scope | Módulo |
|-------|--------|
| `competitors` | functions/competitors/ |
| `checkpoints` | functions/checkpoints/ |
| `events` | functions/events/ |
| `users` | functions/users/ |
| `tracking` | functions/tracking/ |
| `vehicles` | functions/vehicles/ |
| `catalogs` | functions/catalogs/ |
| `staff` | functions/staff/ |
| `models` | functions/models/ |
| `utils` | functions/utils/ |
| `tests` | functions/tests/ |
| `ci` | Scripts, firebase.json, requirements.txt |

---

## Ejemplos de mensajes de commit

```bash
# Nuevo endpoint
feat(competitors): add get_competitor_stats endpoint

# Fix de bug
fix(users): handle missing email field in create_user

# Tests nuevos
test(checkpoints): add coverage for update_competitor_status edge cases

# Documentación
docs(competitors): add README with all endpoint examples

# Refactor sin cambio de comportamiento
refactor(competitors): extract _get_collection_path to competitor_helper

# Nueva colección en FirestoreCollections
feat(models): add PARTICIPANT_RESULTS collection constant

# Helper nuevo
feat(utils): add time_helper with calculate_final_time

# Múltiples módulos en un commit (usar scope más general)
feat(competitors): add register_result and update_score endpoints

# Breaking change (raro — documentar en body)
feat(events)!: change event_categories response to return flat array

BREAKING CHANGE: event_categories now returns List[str] instead of List[{id, name}].
Update all clients that consume this endpoint.
```

---

## Proceso de commit

### Paso 1 — Verificar estado

```bash
git status
git diff --stat
```

### Paso 2 — Staging

```bash
# Archivos específicos (preferido sobre git add .)
git add functions/competitors/get_competitor_stats.py
git add functions/tests/test_competitors_get_competitor_stats.py
git add functions/main.py
git add functions/models/firestore_collections.py
git add functions/competitors/README.md
git add ai-system/changes/competitors/verify-report.md
```

### Paso 3 — Commit

```bash
git commit -m "feat(competitors): add get_competitor_stats endpoint

- GET /get_competitor_stats with eventId and competitorId params
- Returns JSON object with totalTime, finalTime, status
- 95% test coverage
- Updated competitors/README.md"
```

### Paso 4 — Push

```bash
git push origin <branch>
```

---

## Reglas de commits

1. **Siempre en imperativo** — "add", "fix", "update", nunca "added", "fixed"
2. **Scope siempre en minúsculas** — `(competitors)` no `(Competitors)`
3. **Descripción <= 72 caracteres** en la primera línea
4. **Body opcional** — para cambios complejos o breaking changes
5. **Nunca incluir** archivos de entorno (`.env`, `serviceAccountKey.json`, `venv/`)
6. **Nunca hacer `git add .`** sin revisar `git status` primero — puede incluir archivos sensibles

---

## Archivos a NO incluir en commits

```
.env
*serviceAccountKey*.json
venv/
__pycache__/
*.pyc
.firebase/
functions/.ruff_cache/
```

Si alguno aparece en `git status`, añadirlo a `.gitignore` antes de hacer commit.

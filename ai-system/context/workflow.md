# Workflow — Sport Monitor Cloud Functions

## SDD adaptado para Python/Firebase

SDD (Structured Development Driven) para este proyecto tiene 3 fases opcionales
antes de la implementación y 3 waves de ejecución obligatorias.

---

## Phase Decision Table

| Situación | Fase requerida |
|-----------|---------------|
| Función nueva simple (1 endpoint, lógica clara) | Ir directo a Wave 1 |
| Función nueva con múltiples colecciones o lógica compleja | /plan primero |
| Módulo existente que se va a extender significativamente | /sdd_explore + /sdd_design |
| Cambio que afecta contratos HTTP ya publicados | /sdd_design + /sdd_verify post |
| Refactor de lógica interna sin cambiar contrato | /sdd_explore opcional |
| Bug fix en función existente | Ir directo a Wave 1 |
| Nuevas colecciones Firestore | /plan + añadir a FirestoreCollections primero |

---

## Fases pre-implementación (opcionales según tabla)

### /plan — Plan estructurado

Usar antes de implementar cuando el cambio involucra:
- Más de 2 endpoints nuevos
- Nuevas colecciones Firestore
- Cambios en helpers compartidos
- Lógica de negocio compleja

Output del plan:
1. Endpoints a crear/modificar (tabla: método, path, región, módulo, archivo)
2. Colecciones Firestore afectadas
3. Helpers a reutilizar o crear
4. Registro en main.py necesario
5. Wave plan con dependencias

### /sdd_explore — Exploración de módulo existente

Usar cuando el módulo ya existe y se va a extender.
Lee los archivos del módulo, identifica patrones actuales y desviaciones.
Output: `ai-system/changes/<module>/explore.md`

### /sdd_design — Diseño de contratos HTTP

Usa cuando los contratos HTTP necesitan ser definidos y aprobados antes de implementar.
Output: `ai-system/changes/<module>/design.md`

---

## Wave execution — SIEMPRE este orden

### Wave 1 (parallel) — Registro + Implementación

Los dos agentes corren en paralelo porque sus responsabilidades son independientes.

**functions-cross** hace:
- Añadir constantes nuevas a `models/firestore_collections.py`
- Crear o modificar modelos en `models/`
- Crear helpers reutilizables en `utils/` si aplica
- Registrar la función en `functions/main.py` (import + export)

**functions-endpoint** hace:
- Crear `<module>/<verb>_<resource>.py` con el template obligatorio
- Aplicar `validate_request` + `verify_bearer_token` + early return
- Implementar lógica de negocio con `FirestoreHelper`
- Separar lógica en funciones auxiliares `_privadas`

### Wave 2 (sequential) — Tests

Depende de que Wave 1 esté completo.

**functions-test** hace:
- Crear `tests/test_<module>_<function>.py`
- Fixtures para mock_validate_request, mock_verify_bearer_token, mock_firestore_helper
- Casos obligatorios: happy path, 400 parámetros faltantes, 401 token inválido,
  query con data, múltiples llamadas
- Cobertura >= 90%

Comando de verificación:
```bash
pytest functions/tests/test_<module>_<function>.py -v --cov=functions/<module> --cov-fail-under=90
```

### Wave 3 (sequential, SIEMPRE OBLIGATORIO)

**functions-docs** hace:
- Crear o actualizar `functions/<module>/README.md`
- Documentar: endpoint, método HTTP, URL, headers, parámetros, respuesta, errores, curl examples
- Si el módulo ya tiene README, hacer append al changelog

---

## Hard rules (nunca negociables)

1. **Template obligatorio** — toda función con `validate_request` + `verify_bearer_token` + early return
2. **CORS en toda respuesta** — `Access-Control-Allow-Origin: *` siempre, éxito y error
3. **Early return** — nunca anidar if/else para validaciones
4. **JSON directo** — sin wrappers `success`, `data`, `message` en éxito
5. **Errores vacíos** — sin JSON en body de error (solo código HTTP)
6. **FirestoreCollections** — nunca strings hardcodeados para colecciones
7. **FirestoreHelper** — nunca `firestore.client()` directo en endpoints
8. **Wave 3 obligatoria** — nunca saltar la documentación
9. **Cobertura >= 90%** — tests siempre antes del deploy

---

## Ciclo completo de trabajo

```
1. Recibir request del usuario
       ↓
2. Aplicar Phase Decision Table
   ├── ¿Simple? → ir a Wave 1 directo
   └── ¿Complejo? → /plan → [/sdd_explore] → [/sdd_design] → Wave 1
       ↓
3. Wave 1 (parallel)
   ├── functions-cross: FirestoreCollections + main.py + modelos + utils
   └── functions-endpoint: implementar handler con template obligatorio
       ↓
4. Wave 2: functions-test
   └── tests/test_<module>_<function>.py — cobertura >= 90%
       ↓
5. /sdd_verify (pre-deploy checklist)
       ↓
6. Wave 3: functions-docs
   └── README del módulo actualizado
       ↓
7. /push — commit con Conventional Commits
       ↓
8. firebase deploy --only functions:<nombre>
```

---

## Ejemplo — nuevo endpoint GET simple

Request: "Añadir endpoint para obtener el detalle de un checkpoint por ID"

```
Phase: Simple → ir directo a Wave 1

Wave 1:
  functions-cross:
    - FirestoreCollections: ya existe EVENT_CHECKPOINTS — no añadir
    - main.py: añadir "from checkpoints import get_checkpoint_detail"

  functions-endpoint:
    - Crear: functions/checkpoints/get_checkpoint_detail.py
    - Template con region="us-east4", método GET
    - Params: eventId (requerido), checkpointId (requerido)
    - helper.get_document(path, checkpointId) → 404 si None
    - Retornar objeto JSON directo

Wave 2:
  - tests/test_checkpoints_get_checkpoint_detail.py
  - happy path, missing eventId, missing checkpointId, 401, 404, 500

Wave 3:
  - functions/checkpoints/README.md — añadir sección del nuevo endpoint
```

---

## Ejemplo — nuevo endpoint POST complejo

Request: "Añadir endpoint para registrar resultado de un competidor con validaciones"

```
Phase: Complejo → /plan primero

Plan output:
  - Endpoints: POST /register_result (us-east4, competitors/)
  - Colecciones: EVENT_PARTICIPANTS (ya existe), EVENT_TRACKING (ya existe)
  - Nuevas colecciones: PARTICIPANT_RESULTS → añadir a FirestoreCollections
  - Helpers: get_current_timestamp() (ya existe), validate_required_fields() (ya existe)
  - main.py: añadir import de register_result

Wave 1:
  functions-cross:
    - FirestoreCollections.PARTICIPANT_RESULTS = "results"
    - main.py: from competitors import register_result

  functions-endpoint:
    - Crear: functions/competitors/register_result.py
    - Template con region="us-east4", método POST
    - Body: eventId, competitorId, time, category (todos requeridos)
    - validate_required_fields(body, [...]) → 400 si falta alguno
    - helper.create_document(...) con timestamp
    - Retornar {"id": new_id, ...} JSON directo

Wave 2:
  - tests/test_competitors_register_result.py

Wave 3:
  - functions/competitors/README.md — nuevo endpoint

/push: feat(competitors): add register_result endpoint
firebase deploy --only functions:register_result
```

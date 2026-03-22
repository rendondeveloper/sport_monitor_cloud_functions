# Skill: /plan

**Categoria**: Workflow
**Agente responsable**: architect

---

## Cuando usar este skill

- Antes de implementar 2 o más endpoints nuevos
- Cuando el cambio involucra nuevas colecciones Firestore
- Cuando hay lógica de negocio compleja (flujos A+B, validaciones cruzadas)
- Cuando se modifica un helper compartido que afecta múltiples módulos
- Cuando hay incertidumbre sobre el diseño de la respuesta HTTP

Para cambios simples (1 endpoint, lógica clara, colecciones ya existentes),
ir directo a Wave 1 sin /plan.

---

## Proceso

1. Leer el request del usuario
2. Leer contexto relevante:
   - `functions/main.py` — funciones registradas
   - `functions/models/firestore_collections.py` — colecciones existentes
   - Módulo afectado (si ya existe)
3. Producir plan estructurado

---

## Output format

```markdown
## Plan: <titulo del cambio>

### Summary
<Una o dos oraciones describiendo qué se va a implementar>

### Endpoints a crear/modificar

| Método | Función | Módulo | Archivo | Región | Acción |
|--------|---------|--------|---------|--------|--------|
| GET | get_event_stats | events/ | get_event_stats.py | us-central1 | Crear |
| PUT | update_competitor_status | checkpoints/ | update_competitor_status.py | us-east4 | Modificar |

### Colecciones Firestore afectadas

| Constante | Valor string | Path de ejemplo | Existe |
|-----------|-------------|----------------|--------|
| EVENT_PARTICIPANTS | participants | events/{id}/participants | Si |
| PARTICIPANT_RESULTS | results | events/{id}/participants/{id}/results | No — añadir |

Colecciones nuevas a añadir en FirestoreCollections:
```python
PARTICIPANT_RESULTS = "results"
```

### Helpers a reutilizar

| Helper | Función | Import |
|--------|---------|--------|
| datetime_helper | get_current_timestamp() | timestamps |
| helpers | convert_firestore_value() | campos de fecha |
| validation_helper | validate_required_fields() | validación de body POST |

### Registro en main.py

```python
# Bloque competitors — añadir:
from competitors import (
    # ... existentes ...
    nueva_funcion,
)
```

### Wave plan

```
Wave 1 (parallel):
  functions-cross:
    1. Añadir PARTICIPANT_RESULTS = "results" en FirestoreCollections
    2. Registrar nueva_funcion en main.py

  functions-endpoint:
    1. Crear functions/competitors/nueva_funcion.py
    2. Template: region=us-east4, método GET
    3. Params: eventId (requerido), userId (requerido)
    4. helper.get_document(path, userId) → 404 si None
    5. Retornar objeto JSON directo

Wave 2:
  functions-test:
    - tests/test_competitors_nueva_funcion.py
    - Casos: happy path, eventId faltante, userId faltante, 401, 404, 500

Wave 3 (OBLIGATORIO):
  functions-docs:
    - Actualizar functions/competitors/README.md
```

### Open questions

- [ ] ¿El campo `score` es nullable o siempre tiene valor?
- [ ] ¿Retornar 404 si no hay resultados o array vacío con 200?

*Si no hay preguntas, omitir esta sección.*
```

---

## Reglas del plan

- El plan no escribe código — solo describe qué debe hacer cada agente
- Si hay colecciones nuevas, especificar el nombre exacto antes de implementar
- Siempre incluir Wave 3 (docs) — nunca omitir
- Si hay open questions, esperar respuesta del usuario antes de continuar con Wave 1

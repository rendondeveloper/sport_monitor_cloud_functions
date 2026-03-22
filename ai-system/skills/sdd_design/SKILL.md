# Skill: /sdd_design

**Categoria**: Workflow
**Output**: `ai-system/changes/<module>/design.md`

---

## Cuando usar

- Contratos HTTP que necesitan aprobación antes de implementar
- Endpoints que cambian respuestas existentes (breaking changes)
- Nuevas colecciones Firestore con estructura de documento a definir
- Features grandes donde el backend y frontend deben alinear contratos primero

---

## Proceso

1. Leer el plan (`ai-system/changes/<module>/explore.md` si existe)
2. Diseñar contratos HTTP concretos
3. Diseñar estructura de documentos Firestore
4. Crear `ai-system/changes/<module>/design.md`
5. Esperar aprobación antes de Wave 1

---

## Output: design.md

```markdown
# Design: <feature>

**Fecha**: YYYY-MM-DD
**Módulo**: competitors/
**Estado**: DRAFT | APROBADO | IMPLEMENTADO

---

## Endpoints

### GET /get_competitor_stats

**Función**: `get_competitor_stats`
**Archivo**: `functions/competitors/get_competitor_stats.py`
**Región**: `us-east4`

**Headers**:
| Header | Tipo | Requerido |
|--------|------|-----------|
| Authorization | string (Bearer) | Si |

**Query Parameters**:
| Parámetro | Tipo | Requerido | Validación |
|-----------|------|-----------|-----------|
| eventId | string | Si | No vacío |
| competitorId | string | Si | No vacío |

**Response 200**:
```json
{
  "id": "competitor_uid",
  "eventId": "event123",
  "totalTime": 3600.5,
  "penaltyTime": 30.0,
  "finalTime": 3630.5,
  "checkpointsPassed": 5,
  "status": "finished",
  "updatedAt": "2026-03-21T15:00:00"
}
```

**Response errors**:
| Código | Causa |
|--------|-------|
| 400 | eventId o competitorId faltante |
| 401 | Token inválido |
| 404 | Competidor no encontrado en el evento |
| 500 | Error interno |

---

### POST /register_checkpoint_result

**Función**: `register_checkpoint_result`
**Archivo**: `functions/checkpoints/register_checkpoint_result.py`
**Región**: `us-east4`

**Body (JSON)**:
```json
{
  "eventId": "event123",
  "competitorId": "uid123",
  "checkpointId": "cp_001",
  "time": 1800.5,
  "penalty": 0
}
```

**Campos**:
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| eventId | string | Si | ID del evento |
| competitorId | string | Si | UID del competidor |
| checkpointId | string | Si | ID del checkpoint |
| time | number | Si | Tiempo en segundos |
| penalty | number | No | Penalizaciones (default: 0) |

**Response 201**:
```json
{
  "id": "result_auto_id",
  "competitorId": "uid123",
  "checkpointId": "cp_001",
  "time": 1800.5,
  "penalty": 0,
  "createdAt": "2026-03-21T15:00:00"
}
```

---

## Firestore Document Structure

### events/{eventId}/participants/{competitorId}/results/{resultId}

```json
{
  "competitorId": "uid123",
  "checkpointId": "cp_001",
  "time": 1800.5,
  "penalty": 0,
  "createdAt": "Timestamp",
  "updatedAt": "Timestamp"
}
```

**Nueva constante en FirestoreCollections**:
```python
PARTICIPANT_RESULTS = "results"
```

---

## Preguntas de diseño resueltas

- **¿Retornar 404 o [] para lista vacía?** → Lista vacía con 200 para GET de listas,
  404 solo para GET de objeto único.
- **¿penalty puede ser null?** → No, siempre incluirlo con default 0.
- **¿Quién calcula finalTime?** → El endpoint lo calcula: `time + (penalty * 10)`.

---

## Cambios a FirestoreCollections

```python
# Añadir en models/firestore_collections.py
PARTICIPANT_RESULTS = "results"  # results bajo participants/{id}
```

---

## Aprobación

- [ ] Contratos HTTP aprobados por equipo
- [ ] Estructura Firestore aprobada
- [ ] Sin breaking changes en endpoints existentes (o breaking change documentado)
```

---

## Reglas del design

- El design.md es el contrato — si cambia durante implementación, actualizar el archivo
- Marcar estado: DRAFT → APROBADO → IMPLEMENTADO
- Nunca implementar sin estado APROBADO para features grandes
- Los response shapes deben ser JSON real (no descripciones vagas)

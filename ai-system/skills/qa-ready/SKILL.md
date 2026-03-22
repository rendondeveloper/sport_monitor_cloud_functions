# Skill: /qa-ready

**Categoria**: Testing
**Output**: `ai-system/changes/<module>/verify-report.md`

---

## Cuando usar

Antes de hacer deploy de un cambio importante:
- Feature nueva con 2+ endpoints
- Cambio que modifica respuestas de endpoints existentes
- Hotfix crítico en producción

---

## Proceso

1. Listar todos los endpoints afectados por el cambio
2. Ejecutar tests y capturar resultado de cobertura
3. Verificar checklist de `/sdd_verify`
4. Generar ejemplos cURL reales para QA manual
5. Crear `ai-system/changes/<module>/verify-report.md`

---

## Template verify-report.md

```markdown
# QA Report: <feature>

**Fecha**: YYYY-MM-DD
**Módulo**: competitors/
**Tipo de cambio**: Nueva función / Modificación / Bugfix
**Endpoints afectados**: get_competitor_stats, register_checkpoint_result

---

## Estado general: LISTO / BLOQUEADO

---

## Tests

### Resultado de cobertura

```bash
# Comando ejecutado:
pytest functions/tests/test_competitors_get_competitor_stats.py -v \
  --cov=functions/competitors --cov-report=term-missing --cov-fail-under=90

# Output:
Name                                          Stmts   Miss  Cover
-----------------------------------------------------------------
functions/competitors/get_competitor_stats.py    42      2    95%
-----------------------------------------------------------------
TOTAL                                            42      2    95%

✅ PASS — cobertura 95% >= 90%
```

### Casos cubiertos

| Test | Status |
|------|--------|
| Happy path — lista con 2 items | PASS |
| Lista vacía → 200 [] | PASS |
| eventId faltante → 400 | PASS |
| eventId vacío → 400 | PASS |
| Token inválido → 401 | PASS |
| RuntimeError → 500 | PASS |
| ValueError → 400 | PASS |
| Verificar campos en respuesta | PASS |
| Múltiples llamadas | PASS |

---

## Verificación manual con cURL

### GET get_competitor_stats — Happy Path

```bash
# Emulador local
curl -X GET \
  "http://127.0.0.1:5001/<project-id>/us-east4/get_competitor_stats?eventId=event123&competitorId=uid456" \
  -H "Authorization: Bearer <token>" \
  | python3 -m json.tool

# Respuesta esperada (200):
{
  "id": "uid456",
  "eventId": "event123",
  "totalTime": 3600.5,
  "finalTime": 3630.5,
  "status": "active"
}
```

### GET get_competitor_stats — Missing eventId

```bash
curl -X GET \
  "http://127.0.0.1:5001/<project-id>/us-east4/get_competitor_stats?competitorId=uid456" \
  -H "Authorization: Bearer <token>" \
  -w "\nHTTP Status: %{http_code}\n"

# Respuesta esperada: HTTP Status: 400, body vacío
```

### GET get_competitor_stats — Token inválido

```bash
curl -X GET \
  "http://127.0.0.1:5001/<project-id>/us-east4/get_competitor_stats?eventId=event123&competitorId=uid456" \
  -H "Authorization: Bearer invalid_token" \
  -w "\nHTTP Status: %{http_code}\n"

# Respuesta esperada: HTTP Status: 401, body vacío
```

### POST register_checkpoint_result — Happy Path

```bash
curl -X POST \
  "http://127.0.0.1:5001/<project-id>/us-east4/register_checkpoint_result" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "event123",
    "competitorId": "uid456",
    "checkpointId": "cp_001",
    "time": 1800.5,
    "penalty": 0
  }' \
  | python3 -m json.tool

# Respuesta esperada (201):
{
  "id": "auto_generated_id",
  "competitorId": "uid456",
  "checkpointId": "cp_001",
  "time": 1800.5,
  "penalty": 0,
  "createdAt": "2026-03-21T15:00:00"
}
```

### POST register_checkpoint_result — Body vacío

```bash
curl -X POST \
  "http://127.0.0.1:5001/<project-id>/us-east4/register_checkpoint_result" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n"

# Respuesta esperada: HTTP Status: 400, body vacío
```

---

## Checklist de calidad

### Código

- [ ] Template completo en todos los endpoints (validate_request + verify_bearer_token + early return)
- [ ] CORS headers en TODA respuesta
- [ ] JSON directo en éxito (sin wrappers success/data/message)
- [ ] Errores con body vacío
- [ ] FirestoreCollections para colecciones
- [ ] FirestoreHelper para CRUD
- [ ] Logging con LOG_PREFIX
- [ ] Max 200 líneas por archivo

### Tests

- [ ] Cobertura >= 90%
- [ ] Todos los casos obligatorios cubiertos
- [ ] Tests pasan sin errores: `pytest functions/tests/ -v`

### Documentación

- [ ] README del módulo actualizado (Wave 3)
- [ ] Changelog con fecha

### Deploy

- [ ] Registrado en main.py
- [ ] Región correcta en decorator
- [ ] Comando de deploy listo:
  ```bash
  firebase deploy --only functions:get_competitor_stats,register_checkpoint_result
  ```

---

## Issues encontrados y resueltos

| ID | Severidad | Descripción | Resuelto |
|----|-----------|-------------|---------|
| 1 | CRITICO | get_competitor_stats retornaba JSON en error 404 | Si |
| 2 | MENOR | LOG_PREFIX faltaba en register_checkpoint_result | Si |

---

## Aprobación de QA

- [ ] QA manual completado con cURLs anteriores
- [ ] Todos los issues CRITICOS resueltos
- [ ] Listo para: `firebase deploy --only functions:<names>`
```

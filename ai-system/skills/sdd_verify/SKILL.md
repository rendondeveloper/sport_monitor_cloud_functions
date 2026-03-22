# Skill: /sdd_verify

**Categoria**: Workflow
**Output**: `ai-system/changes/<module>/verify-report.md`

---

## Cuando usar

Después de Wave 2 (tests), antes de Wave 3 (docs) y deploy.
Especialmente importante para:
- Features nuevas con múltiples endpoints
- Cambios en contratos HTTP existentes
- Módulos que nunca tuvieron /sdd_verify antes

---

## Checklist post-implementación

Revisar cada función implementada contra esta lista:

### Template obligatorio

- [ ] `validate_request()` es la primera instrucción (antes del try)
- [ ] Se comprueba si `validation_response is not None` con early return
- [ ] `verify_bearer_token()` es la primera instrucción dentro del try
- [ ] Bearer token invalido retorna 401 (no 400, no 403)

### Respuestas HTTP

- [ ] Respuestas exitosas retornan JSON directo (sin wrappers `success`, `data`, `message`)
- [ ] Listas vacías retornan `json.dumps([])` con 200 (no 404)
- [ ] Objeto no encontrado retorna status 404 con body vacío `""`
- [ ] Errores retornan body vacío `""` (no JSON de error)
- [ ] Creación exitosa retorna 201 (no 200) — si aplica

### CORS

- [ ] CORS headers presentes en TODAS las respuestas (éxito y error)
- [ ] `Access-Control-Allow-Origin: *` en cada return statement
- [ ] OPTIONS preflight manejado por validate_request() (no hay que manejarlo manualmente)

### Early Return

- [ ] No hay if/else anidados para validaciones
- [ ] Cada validación faltante retorna inmediatamente
- [ ] La lógica principal está al mismo nivel de indentación que las validaciones

### Firestore

- [ ] `FirestoreCollections.<CONSTANTE>` para todos los nombres de colección
- [ ] No hay strings hardcodeados de colecciones (`"events"`, `"users"`, etc.)
- [ ] `FirestoreHelper()` para todo CRUD
- [ ] No hay `firestore.client()` directo en el endpoint

### Código

- [ ] Lógica de transformación en funciones auxiliares `_privadas`
- [ ] No más de 200 líneas en el archivo
- [ ] Logging con `LOG_PREFIX` en warnings y errors
- [ ] No hay `print()` en el código
- [ ] `ensure_ascii=False` en todos los `json.dumps()`

### Registro

- [ ] Función registrada en `main.py` con import correcto
- [ ] Nombre de la variable importada coincide con nombre del decorator

### Tests

- [ ] Existe `tests/test_<module>_<function>.py`
- [ ] Cobertura >= 90% (`pytest --cov-fail-under=90`)
- [ ] Happy path cubierto
- [ ] 400 por parámetros faltantes cubierto
- [ ] 401 por token inválido cubierto
- [ ] 404 por recurso no encontrado cubierto (si aplica GET objeto)
- [ ] 500 por excepción interna cubierto
- [ ] Múltiples llamadas cubierto

### Documentación

- [ ] `functions/<module>/README.md` actualizado (Wave 3)
- [ ] Parámetros documentados
- [ ] Response shape documentado
- [ ] Ejemplo cURL incluido

---

## Output: verify-report.md

```markdown
# Verify Report: <feature>

**Fecha**: YYYY-MM-DD
**Módulo**: competitors/
**Funciones verificadas**: get_competitor_stats, register_checkpoint_result

---

## Resultado: PASS / FAIL

### Checklist completado

**Template obligatorio**: PASS
**Respuestas HTTP**: PASS
**CORS**: PASS
**Early Return**: PASS
**Firestore**: PASS
**Código**: PASS
**Registro en main.py**: PASS
**Tests**: PASS (cobertura: 94%)
**Documentación**: PENDIENTE (Wave 3)

### Issues encontrados

| Severidad | Función | Descripción | Corregido |
|-----------|---------|-------------|-----------|
| CRITICO | get_competitor_stats | Retorna {"success": True, "data": {...}} — viola regla 2 | Si |
| CRITICO | register_checkpoint_result | Falta CORS header en return 400 | Si |
| MENOR | get_competitor_stats | LOG_PREFIX usa print() — cambiar a LOG.warning | Si |

### Comandos de verificación ejecutados

```bash
# Tests con cobertura
pytest functions/tests/test_competitors_get_competitor_stats.py -v --cov=functions/competitors --cov-fail-under=90

# Output: 94% coverage — PASS

# Linting
flake8 functions/competitors/get_competitor_stats.py --max-line-length=100
# Output: 0 errores — PASS
```

### Listo para deploy

- [ ] Todos los issues CRITICOS corregidos
- [ ] Tests pasando con cobertura >= 90%
- [ ] Wave 3 (docs) completada
- [ ] Comando de deploy: `firebase deploy --only functions:get_competitor_stats,register_checkpoint_result`
```

---

## Cómo ejecutar verificación de cobertura

```bash
# Función específica
pytest functions/tests/test_<module>_<function>.py -v \
  --cov=functions/<module>/<function_file> \
  --cov-report=term-missing \
  --cov-fail-under=90

# Módulo completo
pytest functions/tests/ -v -k "<module>" \
  --cov=functions/<module> \
  --cov-fail-under=90

# Todos los tests
pytest functions/tests/ -v \
  --cov=functions \
  --cov-report=html \
  --cov-fail-under=90
```

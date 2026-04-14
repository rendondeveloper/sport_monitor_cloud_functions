---
name: deploy
description: Pre-flight checks (tests, verify, docs) + deploy de funciones individuales o todas + post-deploy validation. Nunca deployar sin pasar todos los gates. Usar después de /push cuando el código está en el branch correcto.
---

# Skill: /deploy

**Categoría**: Proceso
**Output**: Función(es) deployada(s) en Firebase Cloud Functions

---

## Cuando usar

- Después de `/push` — código commiteado y en el branch correcto
- Cuando se necesita actualizar funciones en producción o staging
- Cuando hay un hotfix que necesita deploy inmediato (aún así pasan los checks)

---

## Proceso completo

### Fase 1 — Pre-flight checks (obligatorios, nunca omitir)

#### 1.1 Identificar funciones a deployar

Preguntar al usuario o inferir del último commit:

```bash
# Ver último commit para saber qué cambió
git log -1 --stat
```

Determinar qué funciones fueron modificadas:

| Tipo de cambio | Funciones a deployar |
|---------------|---------------------|
| Endpoint nuevo | Solo la función nueva |
| Endpoint modificado | Solo la función modificada |
| Helper en utils/ | TODAS las funciones que lo importan |
| Modelo en models/ | TODAS las funciones que lo importan |
| FirestoreCollections | TODAS las funciones (deploy completo) |
| main.py import nuevo | Solo la función nueva añadida |

#### 1.2 Verificar tests

```bash
# Funciones específicas — cobertura del módulo afectado
pytest functions/tests/ -v -k "<module>" \
  --cov=functions/<module> \
  --cov-report=term-missing \
  --cov-fail-under=90

# O todos los tests si el cambio es transversal
pytest functions/tests/ -v --cov=functions --cov-fail-under=90
```

**Gate:** Si algún test falla → STOP. No deployar. Reportar el fallo.
**Gate:** Si cobertura < 90% → STOP. No deployar. Indicar qué falta.

#### 1.3 Verificar documentación

Comprobar que existe y está actualizado el README del módulo afectado:

- [ ] `functions/<module>/README.md` existe
- [ ] El endpoint nuevo/modificado está documentado
- [ ] Response shapes coinciden con la implementación actual

**Gate:** Si README no existe o está desactualizado → STOP. Ejecutar `/update-readme` primero.

#### 1.4 Verificar que no hay cambios sin commitear

```bash
git status
```

**Gate:** Si hay cambios sin commitear → STOP. Ejecutar `/push` primero.

#### 1.5 Verificar branch

```bash
git branch --show-current
```

Confirmar con el usuario que es el branch correcto para deploy.

---

### Fase 2 — Deploy

#### 2.1 Deploy de función(es) individual(es) (preferido)

```bash
# Una función
firebase deploy --only functions:<function_name>

# Múltiples funciones específicas
firebase deploy --only functions:<fn1>,functions:<fn2>,functions:<fn3>
```

Ejemplos reales del proyecto:

```bash
# Deploy de una función de competitors
firebase deploy --only functions:get_competitors_by_event

# Deploy de funciones de catalogs
firebase deploy --only functions:catalog_route

# Deploy de funciones de tracking
firebase deploy --only functions:track_competitor_position,functions:track_competitors
```

#### 2.2 Deploy completo (solo cuando es necesario)

```bash
# SOLO usar cuando cambian utils/, models/, o FirestoreCollections
firebase deploy --only functions
```

**Advertencia:** El deploy completo redeploya las 31 funciones. Usar solo cuando:
- Cambió `FirestoreCollections` (afecta a todas)
- Cambió un helper de `utils/` usado por múltiples módulos
- Se pide explícitamente un deploy completo

---

### Fase 3 — Post-deploy validation

#### 3.1 Verificar que la función está activa

```bash
# Listar funciones deployadas (requiere gcloud CLI)
firebase functions:list
```

#### 3.2 Test de smoke básico

Generar un curl de prueba para cada función deployada:

```bash
# GET endpoint
curl -s -o /dev/null -w "%{http_code}" \
  "https://<region>-<project-id>.cloudfunctions.net/<function_name>?param=value" \
  -H "Authorization: Bearer <token>"

# POST endpoint
curl -s -o /dev/null -w "%{http_code}" \
  "https://<region>-<project-id>.cloudfunctions.net/<function_name>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

**Resultado esperado:** El endpoint responde (200, 400, o 401 — no 404 ni 500 de deploy).

#### 3.3 Reportar resultado

```
DEPLOY REPORT
════════════════════════════════════════
Date:     YYYY-MM-DD HH:MM
Branch:   <branch>
Commit:   <hash> — <message>

PRE-FLIGHT
  Tests:          PASS (XX% coverage)
  Documentation:  PASS
  Clean tree:     PASS
  Branch:         <branch> ✓

DEPLOYED
  <function_name>  →  <region>  →  OK
  <function_name>  →  <region>  →  OK

POST-DEPLOY
  Smoke test:     PASS / FAIL

STATUS: SUCCESS / FAILED
════════════════════════════════════════
```

---

## Regiones del proyecto

| Módulo | Región |
|--------|--------|
| competitors, checkpoints, catalogs, vehicles | us-east4 |
| events, users, staff, tracking, monitor | us-central1 |

Verificar siempre que la región en el decorator `@https_fn.on_request(region=...)` coincida con la región esperada del módulo.

---

## Gates — Nunca deployar si:

| Condición | Acción |
|-----------|--------|
| Tests fallan | STOP — arreglar tests primero |
| Cobertura < 90% | STOP — añadir tests |
| README no actualizado | STOP — ejecutar `/update-readme` |
| Cambios sin commitear | STOP — ejecutar `/push` |
| Branch incorrecto | STOP — confirmar branch con usuario |
| `/sdd_verify` reportó CRITICAL items | STOP — arreglar CRITICALs primero |
| Smoke test post-deploy falla con 500 | ALERTA — investigar logs inmediatamente |

---

## Comandos rápidos de referencia

```bash
# Deploy individual
firebase deploy --only functions:<name>

# Deploy múltiple
firebase deploy --only functions:<n1>,functions:<n2>

# Deploy todo
firebase deploy --only functions

# Ver logs post-deploy
firebase functions:log --only <function_name>

# Tests antes de deploy
pytest functions/tests/ -v --cov=functions --cov-fail-under=90
```

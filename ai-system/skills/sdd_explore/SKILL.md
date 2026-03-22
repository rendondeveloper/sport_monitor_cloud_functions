# Skill: /sdd_explore

**Categoria**: Workflow
**Output**: `ai-system/changes/<module>/explore.md`

---

## Cuando usar

- Módulo existente que se va a extender con nueva lógica
- Bug complejo donde se necesita entender el código actual antes de modificar
- Refactor donde hay que mapear dependencias

---

## Proceso

1. Leer todos los archivos del módulo (`functions/<module>/`)
2. Leer `functions/<module>/__init__.py` para ver qué se exporta
3. Buscar referencias al módulo en `functions/main.py`
4. Leer tests existentes del módulo en `functions/tests/`
5. Identificar colecciones Firestore que usa el módulo
6. Crear `ai-system/changes/<module>/explore.md`

---

## Output: explore.md

```markdown
# Explore: <module>

**Fecha**: YYYY-MM-DD
**Motivo**: <por qué se está explorando>

## Funciones existentes

| Función | Archivo | Método HTTP | Región | Colecciones |
|---------|---------|-------------|--------|-------------|
| get_competitors_by_event | get_competitors_by_event.py | GET | us-east4 | events/{id}/participants |
| create_competitor | create_competitor.py | POST | us-east4 | events/{id}/participants, users |

## Colecciones Firestore usadas

| Constante | Path | Operaciones |
|-----------|------|-------------|
| EVENTS | events | read |
| EVENT_PARTICIPANTS | events/{id}/participants | read, write |
| USERS | users | read, write |

## Patrones identificados

- Todos los endpoints usan region="us-east4"
- La función _get_collection_path() está duplicada en 3 archivos — candidata a helper
- Los campos de fecha se convierten con convert_firestore_value()
- El LOG_PREFIX sigue el formato "[nombre_funcion]" en todos los archivos

## Desviaciones del estándar

- [ALERTA] create_competitor.py línea 45: usa firestore.client() directo — debería usar FirestoreHelper
- [ALERTA] get_competitor_by_email.py: retorna {"success": True, "data": ...} — viola regla 2
- [OK] Todos los demás archivos siguen el template obligatorio

## Tests existentes

| Archivo test | Función cubierta | Cobertura aprox |
|-------------|-----------------|----------------|
| test_get_competitors_by_event.py | get_competitors_by_event | ~95% |
| test_create_competitor.py | create_competitor | ~88% (falta caso 404) |

## Candidatos a refactoring

- Extraer _get_collection_path() a utils/competitor_helper.py (usada en 3 archivos)
- Corregir desviaciones antes de añadir código nuevo

## Recomendaciones para la implementación

- Seguir el patrón de get_competitors_by_event.py como referencia
- Reutilizar la función _convert_documents_to_list() de get_competitors_by_event.py
```

---

## Reglas del explore

- Documentar desviaciones del estándar — son deuda técnica visible
- Identificar lógica duplicada entre archivos del módulo
- No corregir desviaciones en esta fase — solo documentarlas
- El explore.md sirve de referencia durante la implementación en Wave 1

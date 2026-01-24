# Tarea Jira 1: Agregar constantes de colecciones de vehículos

## Título
[Config] Agregar constantes de colecciones de vehículos a FirestoreCollections

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita agregar las constantes para las colecciones de vehículos en el archivo `FirestoreCollections` para mantener la consistencia y evitar strings hardcodeados en el código de las Cloud Functions del CRUD de vehículos.

## Objetivo

Agregar la constante `USER_VEHICLES` al archivo `functions/models/firestore_collections.py` para representar la subcolección de vehículos de usuarios/competidores.

## Requisitos Técnicos

### Actualización de FirestoreCollections

- [ ] Abrir archivo `functions/models/firestore_collections.py`
- [ ] Agregar constante `USER_VEHICLES = "vehicles"` en la sección de colecciones de usuarios
- [ ] Mantener el formato y estructura existente del archivo
- [ ] Verificar que no haya duplicados
- [ ] La constante debe estar en la sección apropiada (colecciones de usuarios relacionadas)

### Estructura Esperada

```python
class FirestoreCollections:
    # Colecciones principales
    EVENTS = "events"
    USERS = "users"
    EVENT_TRACKING = "events_tracking"

    # Colecciones de eventos relacionados
    EVENT_CHECKPOINTS = "checkpoints"
    DAY_OF_RACES = "day_of_races"
    EVENT_CATEGORIES = "event_categories"
    EVENT_PARTICIPANTS = "participants"
    EVENT_STAFF = "staff_users"
    EVENT_ROUTES = "routes"
    EVENT_CONTENT = "event_content"

    # Colecciones de usuarios relacionados
    USER_VEHICLES = "vehicles"  # ← Nueva constante a agregar

    # Colecciones de tracking
    EVENT_TRACKING_COMPETITOR_TRACKING = "competitor_tracking"
    EVENT_TRACKING_COMPETITOR = "competitors"
    EVENT_TRACKING_CHECKPOINTS = "checkpoints"
```

## Dependencias

- [ ] Esta tarea NO depende de otras tareas

## Criterios de Aceptación

- [ ] Constante `USER_VEHICLES` agregada al archivo
- [ ] Constante sigue el formato de nomenclatura existente
- [ ] Archivo mantiene su estructura y comentarios
- [ ] No hay errores de sintaxis
- [ ] La constante puede importarse correctamente desde otros módulos

## Puntos de Prueba

- [ ] Verificar que la constante se puede importar correctamente: `from models.firestore_collections import FirestoreCollections`
- [ ] Verificar que el valor de la constante es `"vehicles"`
- [ ] Verificar que no hay errores de linting o sintaxis

## Notas Adicionales

- La constante debe estar en la sección de colecciones de usuarios relacionadas
- El valor debe ser `"vehicles"` (en inglés, plural)
- Esta tarea debe completarse antes de crear las Cloud Functions del CRUD de vehículos
- La ruta completa en Firestore será: `users/{userId}/vehicles`
```

# Tarea Jira 6: Crear Cloud Function para obtener información de competidor y ruta

## Título
[Backend] Crear Cloud Function para obtener información de competidor y ruta asignada

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita crear una Cloud Function que obtenga información del competidor y su ruta asignada basándose en múltiples validaciones y consultas a Firestore. El servicio debe validar que el competidor esté activo, que el día esté activo, y encontrar la ruta correcta basándose en la categoría del competidor y el día de carrera.

## Objetivo

Crear una Cloud Function GET que:
- Valide que el competidor existe y está activo (`isAvailable: true`)
- Valide que el día de carrera está activo (`isActivate: true`)
- Obtenga la categoría del competidor desde `competitionCategory.registrationCategory`
- Busque el ID de la categoría en `event_categories` usando el `name`
- Busque la ruta correcta filtrando por `categoryIds` y `dayOfRaceIds`
- Retorne información del competidor y su ruta asignada en formato JSON directo (sin wrappers)

## Requisitos Técnicos

### Cloud Function en Python

- [ ] Crear archivo `functions/competitors/get_competitor_route.py`
- [ ] Crear función `get_competitor_route` con decorador `@https_fn.on_request()`
- [ ] Usar `validate_request()` para validar CORS y método HTTP GET (OBLIGATORIO)
- [ ] Usar `verify_bearer_token()` para autenticación (OBLIGATORIO)
- [ ] Implementar patrón Early Return para validaciones
- [ ] Recibir parámetros dinámicos: `eventId`, `competitorId`, `dayId` (query parameters o path)
- [ ] Validar que todos los parámetros estén presentes y no estén vacíos

### Consultas a Firestore

#### Paso 1: Validar Competidor
- [ ] Conectarse a `events/{eventId}/participants/{competitorId}`
- [ ] Usar `FirestoreCollections.EVENT_PARTICIPANTS` para la colección
- [ ] Validar que el documento existe (si no existe → 404)
- [ ] Validar campo `isAvailable` es `true` (si no está activo → 404)
- [ ] Obtener campos: `competitionCategory.pilotNumber` y `competitionCategory.registrationCategory`
- [ ] Si el competidor no existe → 404
- [ ] Si `isAvailable` es `false` → 404

#### Paso 2: Validar Día de Carrera
- [ ] Conectarse a `events/{eventId}/day_of_races/{dayId}`
- [ ] Usar `FirestoreCollections.DAY_OF_RACES` para la colección
- [ ] Validar que el documento existe (si no existe → 404)
- [ ] Validar campo `isActivate` es `true` (si no está activo → 404)
- [ ] Si el día no existe → 404
- [ ] Si `isActivate` es `false` → 404

#### Paso 3: Obtener ID de Categoría
- [ ] Conectarse a `events/{eventId}/event_categories`
- [ ] Usar `FirestoreCollections.EVENT_CATEGORIES` para la colección
- [ ] Buscar categoría por `name` que coincida con `competitionCategory.registrationCategory`
- [ ] Obtener el `id` de la categoría encontrada
- [ ] Si no se encuentra la categoría → 404

#### Paso 4: Buscar Ruta
- [ ] Conectarse a `events/{eventId}/routes`
- [ ] Usar `FirestoreCollections.EVENT_ROUTES` para la colección
- [ ] Filtrar rutas donde `categoryIds` (array) contenga el `categoryId` obtenido
- [ ] De las rutas filtradas, filtrar donde `dayOfRaceIds` (array) contenga el `dayId`
- [ ] Si no se encuentra ruta → 404
- [ ] Obtener campos: `name` y `routeUrl`

### Respuesta de la API

- [ ] Retornar objeto directo (sin wrapper `success`, `message`, `data`)
- [ ] Formato de respuesta:
```json
{
  "competitor": {
    "category": "ORO",
    "nombre": "25F"
  },
  "route": {
    "name": "ORO ruta",
    "routeUrl": "url"
  }
}
```
- [ ] `competitor.category` = `participants/{competitorId}/competitionCategory/pilotNumber`
- [ ] `competitor.nombre` = `participants/{competitorId}/competitionCategory/registrationCategory`
- [ ] `route.name` = `routes/{routeId}/name`
- [ ] `route.routeUrl` = `routes/{routeId}/routeUrl`
- [ ] Código HTTP 200 para respuesta exitosa
- [ ] Código HTTP 400 para parámetros faltantes o inválidos (sin JSON, solo código)
- [ ] Código HTTP 401 para token inválido (sin JSON, solo código)
- [ ] Código HTTP 404 para recurso no encontrado (competidor, día, categoría o ruta) (sin JSON, solo código)
- [ ] Código HTTP 500 para errores internos (sin JSON, solo código)

### Headers CORS

- [ ] Incluir `Access-Control-Allow-Origin: *`
- [ ] Incluir `Access-Control-Allow-Methods: GET, OPTIONS`
- [ ] Incluir `Access-Control-Allow-Headers: Content-Type, Authorization`
- [ ] Incluir `Content-Type: application/json; charset=utf-8`

### Aislamiento de Tareas

- [ ] Separar lógica de validación de competidor en función auxiliar `_validate_competitor()`
- [ ] Separar lógica de validación de día en función auxiliar `_validate_day_of_race()`
- [ ] Separar lógica de obtención de categoría en función auxiliar `_get_category_id_by_name()`
- [ ] Separar lógica de búsqueda de ruta en función auxiliar `_find_route_by_category_and_day()`
- [ ] Separar lógica de construcción de respuesta en función auxiliar `_build_response()`
- [ ] Función principal solo orquesta validaciones y respuestas

### Logging

- [ ] Logging de información en cada paso de validación
- [ ] Logging de warnings para parámetros faltantes o inválidos
- [ ] Logging de warnings cuando competidor no está activo
- [ ] Logging de warnings cuando día no está activo
- [ ] Logging de errores con `exc_info=True` para errores internos

### Registro de Función

- [ ] Crear archivo `functions/competitors/__init__.py` si no existe
- [ ] Exportar función `get_competitor_route` en `__init__.py`
- [ ] Importar función en `functions/main.py`
- [ ] Agregar ruta en `firebase.json` para hosting (opcional)

### Uso de FirestoreCollections

- [ ] Usar `FirestoreCollections.EVENTS` para la colección principal
- [ ] Usar `FirestoreCollections.EVENT_PARTICIPANTS` para participantes
- [ ] Usar `FirestoreCollections.DAY_OF_RACES` para días de carrera
- [ ] Usar `FirestoreCollections.EVENT_CATEGORIES` para categorías
- [ ] Usar `FirestoreCollections.EVENT_ROUTES` para rutas
- [ ] NO usar strings hardcodeados

## Dependencias

- [ ] Esta tarea NO depende de otras tareas

## Criterios de Aceptación

- [ ] Cloud Function creada y desplegada en Firebase
- [ ] Función usa `validate_request()` y `verify_bearer_token()` correctamente
- [ ] Función valida que el competidor existe y está activo (`isAvailable: true`)
- [ ] Función valida que el día existe y está activo (`isActivate: true`)
- [ ] Función obtiene correctamente el `categoryId` desde `event_categories` usando el `name` de `registrationCategory`
- [ ] Función filtra rutas correctamente por `categoryIds` y `dayOfRaceIds`
- [ ] Función retorna objeto directo con estructura correcta (sin wrappers)
- [ ] Errores retornan solo código HTTP (sin JSON)
- [ ] Función implementa patrón Early Return
- [ ] Lógica separada en funciones auxiliares
- [ ] Función registrada e importada correctamente
- [ ] Documentación agregada al README.md

## Puntos de Prueba

- [ ] Probar con parámetros válidos y competidor activo (debe retornar 200 con datos)
- [ ] Probar con `eventId` faltante (debe retornar 400)
- [ ] Probar con `competitorId` faltante (debe retornar 400)
- [ ] Probar con `dayId` faltante (debe retornar 400)
- [ ] Probar sin token Bearer (debe retornar 401)
- [ ] Probar con token Bearer inválido (debe retornar 401)
- [ ] Probar con `competitorId` que no existe (debe retornar 404)
- [ ] Probar con competidor que tiene `isAvailable: false` (debe retornar 404)
- [ ] Probar con `dayId` que no existe (debe retornar 404)
- [ ] Probar con día que tiene `isActivate: false` (debe retornar 404)
- [ ] Probar con categoría que no existe en `event_categories` (debe retornar 404)
- [ ] Probar con ruta que no existe para la categoría y día (debe retornar 404)
- [ ] Verificar que la respuesta tiene la estructura correcta
- [ ] Verificar que `competitor.category` viene de `pilotNumber`
- [ ] Verificar que `competitor.nombre` viene de `registrationCategory`
- [ ] Verificar que `route.name` y `route.routeUrl` vienen de la ruta encontrada

## Notas Adicionales

- La función debe seguir las reglas definidas en `.cursor/rules/cloud_functions_rules.mdc`
- Rutas en Firestore:
  - `events/{eventId}/participants/{competitorId}` - Validar competidor
  - `events/{eventId}/day_of_races/{dayId}` - Validar día
  - `events/{eventId}/event_categories` - Buscar categoría por name
  - `events/{eventId}/routes` - Buscar ruta por categoryIds y dayOfRaceIds
- Estructura de respuesta:
  - `competitor.category` = `competitionCategory.pilotNumber`
  - `competitor.nombre` = `competitionCategory.registrationCategory`
  - `route.name` = `routes/{routeId}/name`
  - `route.routeUrl` = `routes/{routeId}/routeUrl`
- Usar constantes de `FirestoreCollections` en lugar de strings hardcodeados
- Package sugerido: `competitors` (nuevo package para funciones relacionadas con competidores)
- El campo `name` para buscar la categoría viene de `competitionCategory.registrationCategory`
```

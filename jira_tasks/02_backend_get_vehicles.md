# Tarea Jira 2: Crear Cloud Function GET para obtener vehículos

## Título
[Backend] Crear Cloud Function GET para obtener vehículos de un competidor

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita crear una Cloud Function que permita obtener todos los vehículos de un competidor/usuario desde Firestore. La función debe recibir el UUID del usuario y retornar un array directo de vehículos.

## Objetivo

Crear una Cloud Function GET que:
- Reciba el UUID del usuario como parámetro
- Obtenga todos los vehículos del usuario desde Firestore
- Retorne un array directo de vehículos en formato JSON (sin wrappers)

## Requisitos Técnicos

### Endpoint HTTP

- [ ] **Método HTTP**: `GET`
- [ ] **Path**: `/api/vehicles`
- [ ] **Query Parameters**: `userId` (UUID del usuario, requerido)
- [ ] **Ejemplo de URL**: `https://system-track-monitor.web.app/api/vehicles?userId={userId}`
- [ ] Agregar ruta en `firebase.json` en la sección `hosting.rewrites`:
  ```json
  {
    "source": "/api/vehicles",
    "function": "get_vehicles",
    "region": "us-central1"
  }
  ```

### Package y Ubicación

- [ ] **Package**: `vehicles` (traducido de "vehiculo" a inglés)
- [ ] **Ubicación**: `functions/vehicles/` (NO en la raíz del proyecto)
- [ ] Crear directorio `functions/vehicles/` si no existe

### Cloud Function en Python

- [ ] Crear archivo `functions/vehicles/get_vehicles.py`
- [ ] Crear función `get_vehicles` con decorador `@https_fn.on_request()`
- [ ] Usar `validate_request()` para validar CORS y método HTTP GET (OBLIGATORIO)
- [ ] Usar `verify_bearer_token()` para autenticación (OBLIGATORIO)
- [ ] Implementar patrón Early Return para validaciones
- [ ] Recibir `userId` (UUID del usuario) como query parameter o path parameter
- [ ] Validar que `userId` esté presente y no esté vacío
- [ ] Usar `FirestoreCollections.USERS` para la colección principal
- [ ] Usar `FirestoreCollections.USER_VEHICLES` para la subcolección
- [ ] Construir ruta: `users/{userId}/vehicles`
- [ ] Obtener todos los documentos de la subcolección sin filtros
- [ ] Mapear documentos a formato JSON con campos: `id`, `branch`, `year`, `model`, `color`, `createdAt`, `updatedAt`
- [ ] Usar `convert_firestore_value()` para convertir timestamps a ISO 8601

### Respuesta de la API

- [ ] Retornar array directo de vehículos (sin wrapper `success`, `message`, `data`)
- [ ] Formato de respuesta: `[{id, branch, year, model, color, createdAt, updatedAt}, ...]`
- [ ] Si no hay vehículos, retornar array vacío `[]`
- [ ] Código HTTP 200 para respuesta exitosa
- [ ] Código HTTP 400 para parámetros faltantes (sin JSON, solo código)
- [ ] Código HTTP 401 para token inválido (sin JSON, solo código)
- [ ] Código HTTP 404 para usuario no encontrado (sin JSON, solo código)
- [ ] Código HTTP 500 para errores internos (sin JSON, solo código)

### Headers CORS

- [ ] Incluir `Access-Control-Allow-Origin: *`
- [ ] Incluir `Access-Control-Allow-Methods: GET, OPTIONS`
- [ ] Incluir `Access-Control-Allow-Headers: Content-Type, Authorization`
- [ ] Incluir `Content-Type: application/json; charset=utf-8`

### Aislamiento de Tareas

- [ ] Separar lógica de obtención de Firestore en función auxiliar `_get_vehicles_from_firestore()`
- [ ] Separar lógica de mapeo en función auxiliar `_build_vehicle_dict()`
- [ ] Función principal solo orquesta validaciones y respuestas

### Logging

- [ ] Logging de información al obtener vehículos
- [ ] Logging de warnings para parámetros faltantes o inválidos
- [ ] Logging de errores con `exc_info=True` para errores internos

### Registro de Función

- [ ] Crear archivo `functions/vehicles/__init__.py` si no existe
- [ ] Exportar función `get_vehicles` en `__init__.py`
- [ ] Importar función en `functions/main.py`
- [ ] Agregar ruta en `firebase.json` para hosting (ver sección Endpoint HTTP arriba)

## Dependencias

- [ ] Esta tarea depende de:
  - **TICKET-XX**: Agregar constantes de colecciones de vehículos a FirestoreCollections - debe estar completada

## Criterios de Aceptación

- [ ] Cloud Function creada y desplegada en Firebase
- [ ] Endpoint HTTP configurado en `firebase.json` con path `/api/vehicles`
- [ ] Función usa `validate_request()` y `verify_bearer_token()` correctamente
- [ ] Función retorna array directo de vehículos (sin wrappers)
- [ ] Errores retornan solo código HTTP (sin JSON)
- [ ] Función implementa patrón Early Return
- [ ] Lógica separada en funciones auxiliares
- [ ] Función registrada en `functions/vehicles/__init__.py`
- [ ] Función importada en `functions/main.py`
- [ ] Documentación agregada al README.md

## Puntos de Prueba

- [ ] Probar con `userId` válido que tiene vehículos
- [ ] Probar con `userId` válido sin vehículos (debe retornar array vacío `[]`)
- [ ] Probar con `userId` inválido o faltante (debe retornar 400)
- [ ] Probar sin token Bearer (debe retornar 401)
- [ ] Probar con token Bearer inválido (debe retornar 401)
- [ ] Probar con `userId` que no existe (debe retornar 404)
- [ ] Verificar que la respuesta es un array directo sin wrappers
- [ ] Verificar que los timestamps están en formato ISO 8601

## Notas Adicionales

- La función debe seguir las reglas definidas en `.cursor/rules/cloud_functions_rules.mdc`
- La ruta en Firestore es: `users/{userId}/vehicles`
- Usar constantes de `FirestoreCollections` en lugar de strings hardcodeados
- **Package obligatorio**: `vehicles` - Todos los archivos del CRUD de vehículos deben estar en `functions/vehicles/` (NO en la raíz)
```

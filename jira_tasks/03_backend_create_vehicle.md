# Tarea Jira 3: Crear Cloud Function POST para crear vehículo

## Título
[Backend] Crear Cloud Function POST para crear vehículo de competidor

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita crear una Cloud Function que permita crear un nuevo vehículo para un competidor/usuario en Firestore. La función debe recibir el UUID del usuario, `authUserId` y los datos del vehículo.

## Objetivo

Crear una Cloud Function POST que:
- Reciba el UUID del usuario y `authUserId` como parámetros
- Reciba los datos del vehículo en el request body (Branch, Year, Model, Color)
- Cree un nuevo documento de vehículo en Firestore
- Retorne el vehículo creado en formato JSON (sin wrappers)

## Requisitos Técnicos

### Cloud Function en Python

- [ ] Crear archivo `functions/vehicles/create_vehicle.py`
- [ ] Crear función `create_vehicle` con decorador `@https_fn.on_request()`
- [ ] Usar `validate_request()` para validar CORS y método HTTP POST (OBLIGATORIO)
- [ ] Usar `verify_bearer_token()` para autenticación (OBLIGATORIO)
- [ ] Implementar patrón Early Return para validaciones
- [ ] Recibir `userId` (UUID del usuario) como query parameter o path parameter
- [ ] Recibir `authUserId` como query parameter o en el request body
- [ ] Validar que `userId` y `authUserId` estén presentes y no estén vacíos
- [ ] Validar que el usuario existe en Firestore
- [ ] Validar que el `authUserId` coincide con el usuario
- [ ] Parsear request body JSON
- [ ] Validar campos requeridos: `branch`, `year`, `model`, `color`
- [ ] Validar tipos de datos (year debe ser integer)
- [ ] Usar `FirestoreCollections.USERS` para la colección principal
- [ ] Usar `FirestoreCollections.USER_VEHICLES` para la subcolección
- [ ] Construir ruta: `users/{userId}/vehicles`
- [ ] Crear nuevo documento con campos: `branch`, `year`, `model`, `color`, `createdAt`, `updatedAt`
- [ ] Generar `createdAt` y `updatedAt` con `datetime.utcnow()`

### Request Body

```json
{
  "branch": "string (requerido)",
  "year": "integer (requerido)",
  "model": "string (requerido)",
  "color": "string (requerido)"
}
```

### Respuesta de la API

- [ ] Retornar objeto directo del vehículo creado (sin wrapper `success`, `message`, `data`)
- [ ] Formato de respuesta: `{id, branch, year, model, color, createdAt, updatedAt}`
- [ ] Código HTTP 201 para creación exitosa
- [ ] Código HTTP 400 para parámetros faltantes o inválidos (sin JSON, solo código)
- [ ] Código HTTP 401 para token inválido (sin JSON, solo código)
- [ ] Código HTTP 404 para usuario no encontrado (sin JSON, solo código)
- [ ] Código HTTP 500 para errores internos (sin JSON, solo código)

### Headers CORS

- [ ] Incluir `Access-Control-Allow-Origin: *`
- [ ] Incluir `Access-Control-Allow-Methods: POST, OPTIONS`
- [ ] Incluir `Access-Control-Allow-Headers: Content-Type, Authorization`
- [ ] Incluir `Content-Type: application/json; charset=utf-8`

### Aislamiento de Tareas

- [ ] Separar lógica de validación de usuario en función auxiliar `_validate_user()`
- [ ] Separar lógica de creación en Firestore en función auxiliar `_create_vehicle_in_firestore()`
- [ ] Separar lógica de construcción de datos en función auxiliar `_build_vehicle_data()`
- [ ] Función principal solo orquesta validaciones y respuestas

### Logging

- [ ] Logging de información al crear vehículo
- [ ] Logging de warnings para parámetros faltantes o inválidos
- [ ] Logging de errores con `exc_info=True` para errores internos

### Registro de Función

- [ ] Exportar función `create_vehicle` en `functions/vehicles/__init__.py`
- [ ] Importar función en `functions/main.py`
- [ ] Agregar ruta en `firebase.json` para hosting (opcional)

## Dependencias

- [ ] Esta tarea depende de:
  - **TICKET-XX**: Agregar constantes de colecciones de vehículos a FirestoreCollections - debe estar completada

## Criterios de Aceptación

- [ ] Cloud Function creada y desplegada en Firebase
- [ ] Función usa `validate_request()` y `verify_bearer_token()` correctamente
- [ ] Función valida todos los campos requeridos
- [ ] Función valida que el usuario existe y el `authUserId` coincide
- [ ] Función retorna objeto directo del vehículo creado (sin wrappers)
- [ ] Errores retornan solo código HTTP (sin JSON)
- [ ] Función implementa patrón Early Return
- [ ] Lógica separada en funciones auxiliares
- [ ] Función registrada e importada correctamente
- [ ] Documentación agregada al README.md

## Puntos de Prueba

- [ ] Probar con todos los campos válidos (debe retornar 201 con vehículo creado)
- [ ] Probar con `userId` faltante (debe retornar 400)
- [ ] Probar con `authUserId` faltante (debe retornar 400)
- [ ] Probar con campo `branch` faltante (debe retornar 400)
- [ ] Probar con campo `year` faltante (debe retornar 400)
- [ ] Probar con campo `model` faltante (debe retornar 400)
- [ ] Probar con campo `color` faltante (debe retornar 400)
- [ ] Probar con `year` que no es número (debe retornar 400)
- [ ] Probar sin token Bearer (debe retornar 401)
- [ ] Probar con token Bearer inválido (debe retornar 401)
- [ ] Probar con `userId` que no existe (debe retornar 404)
- [ ] Probar con `authUserId` que no coincide (debe retornar 404 o 400)
- [ ] Verificar que el vehículo se crea correctamente en Firestore
- [ ] Verificar que los timestamps se generan correctamente

## Notas Adicionales

- La función debe seguir las reglas definidas en `.cursor/rules/cloud_functions_rules.mdc`
- La ruta en Firestore es: `users/{userId}/vehicles`
- Campos requeridos: `branch` (string), `year` (integer), `model` (string), `color` (string)
- Usar constantes de `FirestoreCollections` en lugar de strings hardcodeados
- Package: `vehicles` (traducido de "vehiculo" a inglés)
```

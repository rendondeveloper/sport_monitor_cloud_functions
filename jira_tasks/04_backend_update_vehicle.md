# Tarea Jira 4: Crear Cloud Function PUT para actualizar vehículo

## Título
[Backend] Crear Cloud Function PUT para actualizar vehículo de competidor

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita crear una Cloud Function que permita actualizar un vehículo existente de un competidor/usuario en Firestore. La función debe recibir el UUID del usuario, `authUserId`, el UUID del vehículo y los nuevos datos.

## Objetivo

Crear una Cloud Function PUT que:
- Reciba el UUID del usuario, `authUserId` y el UUID del vehículo como parámetros
- Reciba los datos actualizados del vehículo en el request body (Branch, Year, Model, Color)
- Actualice el documento del vehículo en Firestore
- Retorne el vehículo actualizado en formato JSON (sin wrappers)

## Requisitos Técnicos

### Cloud Function en Python

- [ ] Crear archivo `functions/vehicles/update_vehicle.py`
- [ ] Crear función `update_vehicle` con decorador `@https_fn.on_request()`
- [ ] Usar `validate_request()` para validar CORS y método HTTP PUT (OBLIGATORIO)
- [ ] Usar `verify_bearer_token()` para autenticación (OBLIGATORIO)
- [ ] Implementar patrón Early Return para validaciones
- [ ] Recibir `userId` (UUID del usuario) como query parameter o path parameter
- [ ] Recibir `authUserId` como query parameter o en el request body
- [ ] Recibir `vehicleId` (UUID del vehículo) como query parameter o path parameter
- [ ] Validar que `userId`, `authUserId` y `vehicleId` estén presentes y no estén vacíos
- [ ] Validar que el usuario existe en Firestore
- [ ] Validar que el `authUserId` coincide con el usuario
- [ ] Validar que el vehículo existe en Firestore
- [ ] Parsear request body JSON
- [ ] Validar campos requeridos: `branch`, `year`, `model`, `color`
- [ ] Validar tipos de datos (year debe ser integer)
- [ ] Usar `FirestoreCollections.USERS` para la colección principal
- [ ] Usar `FirestoreCollections.USER_VEHICLES` para la subcolección
- [ ] Construir ruta: `users/{userId}/vehicles/{vehicleId}`
- [ ] Actualizar documento con campos: `branch`, `year`, `model`, `color`, `updatedAt`
- [ ] Actualizar `updatedAt` con `datetime.utcnow()`
- [ ] No modificar `createdAt`

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

- [ ] Retornar objeto directo del vehículo actualizado (sin wrapper `success`, `message`, `data`)
- [ ] Formato de respuesta: `{id, branch, year, model, color, createdAt, updatedAt}`
- [ ] Código HTTP 200 para actualización exitosa
- [ ] Código HTTP 400 para parámetros faltantes o inválidos (sin JSON, solo código)
- [ ] Código HTTP 401 para token inválido (sin JSON, solo código)
- [ ] Código HTTP 404 para usuario o vehículo no encontrado (sin JSON, solo código)
- [ ] Código HTTP 500 para errores internos (sin JSON, solo código)

### Headers CORS

- [ ] Incluir `Access-Control-Allow-Origin: *`
- [ ] Incluir `Access-Control-Allow-Methods: PUT, OPTIONS`
- [ ] Incluir `Access-Control-Allow-Headers: Content-Type, Authorization`
- [ ] Incluir `Content-Type: application/json; charset=utf-8`

### Aislamiento de Tareas

- [ ] Separar lógica de validación de usuario en función auxiliar `_validate_user()`
- [ ] Separar lógica de validación de vehículo en función auxiliar `_validate_vehicle()`
- [ ] Separar lógica de actualización en Firestore en función auxiliar `_update_vehicle_in_firestore()`
- [ ] Separar lógica de construcción de datos en función auxiliar `_build_vehicle_update_data()`
- [ ] Función principal solo orquesta validaciones y respuestas

### Logging

- [ ] Logging de información al actualizar vehículo
- [ ] Logging de warnings para parámetros faltantes o inválidos
- [ ] Logging de errores con `exc_info=True` para errores internos

### Registro de Función

- [ ] Exportar función `update_vehicle` en `functions/vehicles/__init__.py`
- [ ] Importar función en `functions/main.py`
- [ ] Agregar ruta en `firebase.json` para hosting (opcional)

## Dependencias

- [ ] Esta tarea depende de:
  - **TICKET-XX**: Agregar constantes de colecciones de vehículos a FirestoreCollections - debe estar completada
  - **TICKET-XX**: Crear Cloud Function POST para crear vehículo - recomendado (para tener datos de prueba)

## Criterios de Aceptación

- [ ] Cloud Function creada y desplegada en Firebase
- [ ] Función usa `validate_request()` y `verify_bearer_token()` correctamente
- [ ] Función valida todos los parámetros y campos requeridos
- [ ] Función valida que el usuario y vehículo existen
- [ ] Función valida que el `authUserId` coincide
- [ ] Función retorna objeto directo del vehículo actualizado (sin wrappers)
- [ ] Errores retornan solo código HTTP (sin JSON)
- [ ] Función implementa patrón Early Return
- [ ] Lógica separada en funciones auxiliares
- [ ] Función registrada e importada correctamente
- [ ] Documentación agregada al README.md

## Puntos de Prueba

- [ ] Probar con todos los campos válidos (debe retornar 200 con vehículo actualizado)
- [ ] Probar con `userId` faltante (debe retornar 400)
- [ ] Probar con `authUserId` faltante (debe retornar 400)
- [ ] Probar con `vehicleId` faltante (debe retornar 400)
- [ ] Probar con campo `branch` faltante (debe retornar 400)
- [ ] Probar con campo `year` faltante (debe retornar 400)
- [ ] Probar con campo `model` faltante (debe retornar 400)
- [ ] Probar con campo `color` faltante (debe retornar 400)
- [ ] Probar con `year` que no es número (debe retornar 400)
- [ ] Probar sin token Bearer (debe retornar 401)
- [ ] Probar con token Bearer inválido (debe retornar 401)
- [ ] Probar con `userId` que no existe (debe retornar 404)
- [ ] Probar con `vehicleId` que no existe (debe retornar 404)
- [ ] Probar con `authUserId` que no coincide (debe retornar 404 o 400)
- [ ] Verificar que el vehículo se actualiza correctamente en Firestore
- [ ] Verificar que `updatedAt` se actualiza pero `createdAt` no cambia

## Notas Adicionales

- La función debe seguir las reglas definidas en `.cursor/rules/cloud_functions_rules.mdc`
- La ruta en Firestore es: `users/{userId}/vehicles/{vehicleId}`
- Campos requeridos: `branch` (string), `year` (integer), `model` (string), `color` (string)
- Usar constantes de `FirestoreCollections` en lugar de strings hardcodeados
- Package: `vehicles` (traducido de "vehiculo" a inglés)
```

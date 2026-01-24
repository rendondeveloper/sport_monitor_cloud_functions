# Tarea Jira 5: Crear Cloud Function DELETE para eliminar vehículo

## Título
[Backend] Crear Cloud Function DELETE para eliminar vehículo de competidor

## Asignado
(Sin asignar - dejar disponible)

## Descripción

```markdown
## Contexto

Se necesita crear una Cloud Function que permita eliminar un vehículo de un competidor/usuario en Firestore. La función debe recibir el UUID del usuario, `authUserId` y el UUID del vehículo.

## Objetivo

Crear una Cloud Function DELETE que:
- Reciba el UUID del usuario, `authUserId` y el UUID del vehículo como parámetros
- Valide que el usuario y vehículo existen
- Elimine el documento del vehículo en Firestore
- Retorne código HTTP 204 (No Content) para eliminación exitosa

## Requisitos Técnicos

### Package y Ubicación

- [ ] **Package**: `vehicles` (traducido de "vehiculo" a inglés)
- [ ] **Ubicación**: `functions/vehicles/` (NO en la raíz del proyecto)
- [ ] Crear directorio `functions/vehicles/` si no existe

### Cloud Function en Python

- [ ] Crear archivo `functions/vehicles/delete_vehicle.py`
- [ ] Crear función `delete_vehicle` con decorador `@https_fn.on_request()`
- [ ] Usar `validate_request()` para validar CORS y método HTTP DELETE (OBLIGATORIO)
- [ ] Usar `verify_bearer_token()` para autenticación (OBLIGATORIO)
- [ ] Implementar patrón Early Return para validaciones
- [ ] Recibir `userId` (UUID del usuario) como query parameter o path parameter
- [ ] Recibir `authUserId` como query parameter
- [ ] Recibir `vehicleId` (UUID del vehículo) como query parameter o path parameter
- [ ] Validar que `userId`, `authUserId` y `vehicleId` estén presentes y no estén vacíos
- [ ] Validar que el usuario existe en Firestore
- [ ] Validar que el `authUserId` coincide con el usuario
- [ ] Validar que el vehículo existe en Firestore
- [ ] Usar `FirestoreCollections.USERS` para la colección principal
- [ ] Usar `FirestoreCollections.USER_VEHICLES` para la subcolección
- [ ] Construir ruta: `users/{userId}/vehicles/{vehicleId}`
- [ ] Eliminar documento del vehículo

### Respuesta de la API

- [ ] Retornar código HTTP 204 (No Content) para eliminación exitosa (sin cuerpo)
- [ ] Código HTTP 400 para parámetros faltantes o inválidos (sin JSON, solo código)
- [ ] Código HTTP 401 para token inválido (sin JSON, solo código)
- [ ] Código HTTP 404 para usuario o vehículo no encontrado (sin JSON, solo código)
- [ ] Código HTTP 500 para errores internos (sin JSON, solo código)

### Headers CORS

- [ ] Incluir `Access-Control-Allow-Origin: *`
- [ ] Incluir `Access-Control-Allow-Methods: DELETE, OPTIONS`
- [ ] Incluir `Access-Control-Allow-Headers: Content-Type, Authorization`

### Aislamiento de Tareas

- [ ] Separar lógica de validación de usuario en función auxiliar `_validate_user()`
- [ ] Separar lógica de validación de vehículo en función auxiliar `_validate_vehicle()`
- [ ] Separar lógica de eliminación en Firestore en función auxiliar `_delete_vehicle_from_firestore()`
- [ ] Función principal solo orquesta validaciones y respuestas

### Logging

- [ ] Logging de información al eliminar vehículo
- [ ] Logging de warnings para parámetros faltantes o inválidos
- [ ] Logging de errores con `exc_info=True` para errores internos

### Registro de Función

- [ ] Exportar función `delete_vehicle` en `functions/vehicles/__init__.py`
- [ ] Importar función en `functions/main.py`
- [ ] Agregar ruta en `firebase.json` para hosting (opcional)

## Dependencias

- [ ] Esta tarea depende de:
  - **TICKET-XX**: Agregar constantes de colecciones de vehículos a FirestoreCollections - debe estar completada
  - **TICKET-XX**: Crear Cloud Function POST para crear vehículo - recomendado (para tener datos de prueba)

## Criterios de Aceptación

- [ ] Cloud Function creada y desplegada en Firebase
- [ ] Función usa `validate_request()` y `verify_bearer_token()` correctamente
- [ ] Función valida todos los parámetros requeridos
- [ ] Función valida que el usuario y vehículo existen
- [ ] Función valida que el `authUserId` coincide
- [ ] Función retorna código HTTP 204 para eliminación exitosa
- [ ] Errores retornan solo código HTTP (sin JSON)
- [ ] Función implementa patrón Early Return
- [ ] Lógica separada en funciones auxiliares
- [ ] Función registrada e importada correctamente
- [ ] Documentación agregada al README.md

## Puntos de Prueba

- [ ] Probar con todos los parámetros válidos (debe retornar 204)
- [ ] Probar con `userId` faltante (debe retornar 400)
- [ ] Probar con `authUserId` faltante (debe retornar 400)
- [ ] Probar con `vehicleId` faltante (debe retornar 400)
- [ ] Probar sin token Bearer (debe retornar 401)
- [ ] Probar con token Bearer inválido (debe retornar 401)
- [ ] Probar con `userId` que no existe (debe retornar 404)
- [ ] Probar con `vehicleId` que no existe (debe retornar 404)
- [ ] Probar con `authUserId` que no coincide (debe retornar 404 o 400)
- [ ] Verificar que el vehículo se elimina correctamente de Firestore
- [ ] Verificar que otros vehículos del usuario no se afectan

## Notas Adicionales

- La función debe seguir las reglas definidas en `.cursor/rules/cloud_functions_rules.mdc`
- La ruta en Firestore es: `users/{userId}/vehicles/{vehicleId}`
- Usar constantes de `FirestoreCollections` en lugar de strings hardcodeados
- **Package obligatorio**: `vehicles` - Todos los archivos del CRUD de vehículos deben estar en `functions/vehicles/` (NO en la raíz)
- La eliminación es permanente (no soft delete)
```

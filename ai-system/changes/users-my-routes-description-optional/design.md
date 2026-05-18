# Diseño — description opcional en POST /api/users/my-routes

## Objetivo

Permitir que `POST /api/users/my-routes` acepte `description` vacío o ausente, evitando `400` en clientes que crean rutas sin descripción.

## Contexto actual (baseline)

- El endpoint público es `user_route` y despacha a `users/create_my_route.py` para `POST /api/users/my-routes`.
- `create_my_route.py` valida actualmente:
  - `userId` requerido
  - `identifier` requerido y `int`
  - `name` requerido y no vacío
  - `description` requerido y no vacío
  - `points` debe ser `list` o `null`
  - `notes` debe ser `list` o `null`
- El documento de ruta ya persiste `description` como string normalizado:
  - `description`: `str(data.get("description", "")).strip()`

## Cambio de contrato

### Endpoint

`POST /api/users/my-routes`

### Body

- `userId`: string (requerido)
- `identifier`: int (requerido)
- `name`: string (requerido)
- `description`: string (opcional)
- `eventId`: any/null (opcional, sin cambios)
- `points`: array|null (opcional)
- `notes`: array|null (opcional)

### Reglas nuevas

- Si `description` no viene en el body, la creación debe continuar.
- Si `description` viene como `""` o solo whitespace, la creación debe continuar.
- El valor persistido en Firestore debe seguir siendo string normalizado:
  - ausente / `null` / whitespace -> `""`
  - string con contenido -> `strip()`

## Respuesta HTTP

- Se mantiene sin cambios:
  - `201` con body `{"id": "<routeId>"}`
  - `400` solo para validaciones restantes
  - `404` si `userId` no existe
  - `500` ante error interno

## Firestore

- Sin cambios de estructura:
  - `users/{userId}/myRoutes/{routeId}`
  - `description` continúa persistiendo al mismo nivel del documento

## Testing (criterios de salida)

Actualizar `functions/tests/test_create_my_route.py` con, mínimo:

- `description` vacío -> `201`
- `description` ausente -> `201`
- `description` con whitespace -> `201` y se persiste `""`
- Mantener cobertura de validaciones restantes (`userId`, `identifier`, `name`, `notes`, `points`)
- Múltiples llamadas seguidas sin regresión

## Docs (criterios de salida)

Actualizar `functions/users/README.md`:

- En `POST /api/users/my-routes`, marcar `description` como opcional.
- Ajustar ejemplo/cURL para reflejar que puede ir vacío o no enviarse.

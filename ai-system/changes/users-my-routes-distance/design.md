# Diseño — distance en POST /api/users/my-routes

## Objetivo

Cuando `POST /api/users/my-routes` reciba `points`, el backend debe calcular `distance` a partir de esos puntos y guardarlo en el documento de la ruta (`users/{userId}/myRoutes/{routeId}`) **al mismo nivel** que `eventId`.

## Contexto actual (baseline)

- El endpoint público es `user_route` y despacha a `users/create_my_route.py` para `POST /api/users/my-routes`.
- `create_my_route.py`:
  - Valida el payload (handler interno, sin CORS/token).
  - Crea `users/{userId}/myRoutes/{routeId}` con campos: `identifier`, `name`, `description`, `eventId`, `pointsCount`, `notesCount`, `createdAt`, `updatedAt`.
  - Crea subdocs en:
    - `users/{userId}/myRoutes/{routeId}/points/*` (auto-id)
    - `users/{userId}/myRoutes/{routeId}/notes/{identifier}` (id = identifier)

## Contrato de entrada (points)

- `points` puede ser `null` o `array`.
- Cada point esperado es dict (objeto) con:
  - `latitude`: number
  - `longitude`: number
- Pueden venir campos extra (altitudeMeters, speedKmh, etc.) y deben preservarse como hoy al guardar subdocs.

## Cálculo de distance

### Definición

- `distance` es un **float** en **kilómetros** con formato tipo **`###.#`** (ej. `55.5`).
- Se calcula como la suma de distancias entre puntos consecutivos válidos (lat/lon numéricos) en el orden recibido, convertido a km y **redondeado hacia arriba** a **1 decimal**.

### Reglas

- Si `points` es `null`, no es lista, o no hay al menos 2 puntos válidos ⇒ `distance = 0.0`.
- Un point es “válido” si:
  - `latitude` y `longitude` existen y son `int` o `float`.
- Puntos inválidos se **ignoran** para el cálculo (no debe fallar la creación de la ruta).
- No se aplica simplificación de ruta, ni filtro por velocidad/tiempo.

### Fórmula

Usar Haversine (gran círculo) con:

- \(R = 6371000.0\) (radio de la Tierra)
- Entradas en radianes
- Salida en metros para cada segmento, sumar, convertir a km: `km = meters / 1000.0`
- Redondeo final (ceiling a 1 decimal): `distance = ceil(km * 10) / 10`

## Persistencia (Firestore)

Documento ruta: `users/{userId}/myRoutes/{routeId}`

- Nuevo campo:
  - `distance`: float (km, ceiling 1 decimal)

No cambia el schema de points/notes, solo el documento de la ruta.

## Respuesta HTTP

- Se mantiene: `201` con body `{"id": "<routeId>"}`.
- No se agregan wrappers ni se cambia el contrato de respuesta.

## Testing (criterios de salida)

Agregar `functions/tests/test_create_my_route.py` con, mínimo:

- Happy path con 2+ points válidos ⇒ `distance > 0` y se incluye en el documento creado.
- `points = null` ⇒ `distance == 0.0`.
- `points` con mezcla de válidos e inválidos ⇒ no falla; distance se calcula con válidos.
- Body inválido ⇒ 400.
- userId no existe ⇒ 404.
- Múltiples llamadas seguidas ⇒ comportamiento estable.

## Docs (criterios de salida)

Actualizar `functions/users/README.md`:

- En `POST /api/users/my-routes`: documentar que se persiste `distance` en el doc de ruta.
- En `GET /api/users/my-routes` (detalle): indicar que el doc incluye `distance` (si existe).


# Handoff — users-my-routes-distance

## Objective

Modificar `functions/users/create_my_route.py` para calcular y guardar `distance: float` en el documento de ruta cuando llega `points` en `POST /api/users/my-routes`.

## Spec (source of truth)

- `ai-system/changes/users-my-routes-distance/design.md`

## Key files

- `functions/users/create_my_route.py` (Wave 1: implementación)
- `functions/tests/test_create_my_route.py` (Wave 2: tests)
- `functions/users/README.md` (Wave 3: docs)

## Implementation notes (must follow)

- `distance` va en el doc `users/{userId}/myRoutes/{routeId}`, al mismo nivel que `eventId`.
- `distance` es `float` en **kilómetros**, con **redondeo hacia arriba** a **1 decimal** (formato tipo `###.#`).
- Cálculo: suma de segmentos Haversine entre puntos consecutivos válidos (lat/lon numéricos), convertir a km y aplicar `ceil(km * 10) / 10`.
- Ignorar puntos inválidos (no romper el endpoint).
- Si no hay 2 puntos válidos, `distance = 0.0`.
- No cambiar la respuesta HTTP (se mantiene `201` y body `{"id": route_id}`).

## Exit criteria

- Code: `distance` se persiste correctamente y el endpoint no rompe inputs existentes.
- Tests: archivo nuevo con cobertura >= 90% para `functions/users/` (en el scope del test) y casos obligatorios.
- Docs: `functions/users/README.md` actualizado documentando `distance`.


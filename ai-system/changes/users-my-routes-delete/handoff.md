# Handoff — users-my-routes-delete

## Objective

Endpoints DELETE para borrar una ruta completa en `myRoutes` o solo sus notas, vía `user_route`.

## Spec

- `ai-system/changes/users-my-routes-delete/design.md`

## Key files

- `functions/users/delete_my_route.py`
- `functions/users/delete_my_route_notes.py`
- `functions/users/user_route.py` (despacho PUT/DELETE en `.../notes`; DELETE en `.../my-routes/{routeId}`)
- `functions/tests/test_delete_my_route.py`, `test_delete_my_route_notes.py`, `test_user_route.py`
- `functions/users/README.md`, `README.md` (§ users / my-routes)

## Deploy

- Último deploy exitoso: `firebase deploy --only functions:user_route,hosting` (proyecto `system-track-monitor`).

## Exit criteria

- Código + tests focalizados pasando; README con cURLs.

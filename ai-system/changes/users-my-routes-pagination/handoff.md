# Handoff — users-my-routes-pagination

## Objective

Agregar paginación al modo lista de `GET /api/users/my-routes` (handler `functions/users/get_my_routes.py`) para controlar volumen de datos, manteniendo compatibilidad hacia atrás para clientes que esperan array.

## Spec (source of truth)

- `ai-system/changes/users-my-routes-pagination/design.md`

## Key files

- `functions/users/get_my_routes.py` (Wave 1: implementación)
- `functions/tests/test_users_get_my_routes.py` (Wave 2: tests)
- `functions/users/README.md` (Wave 3: docs)
- `README.md` (Wave 3: docs raíz, sección 4.1.2 my-routes)

## Implementation notes (must follow)

- **No tocar** el modo detalle por `routeId` (misma respuesta y códigos).
- **Compatibilidad**:
  - Sin `limit` y sin `startAfterDocId` ⇒ retornar **array** (como hoy).
  - Con `limit` o `startAfterDocId` ⇒ retornar JSON paginado (`result` + `pagination`).
- `limit`: default 50, max 100, inválido ⇒ 50.
- `startAfterDocId`: cursor por docId; whitespace ⇒ ignorar.
- Query lista paginada debe ordenar por `createdAt desc` y usar `FirestoreHelper.query_documents(..., limit=..., start_after_doc_id=...)`.
- Respuestas exitosas sin wrappers extra: usar exactamente lo definido en `PaginatedResponse` (`result`, `pagination`).
- Errores: body vacío + CORS, como el resto del módulo.

## Exit criteria

- Code: paginación implementada con compatibilidad hacia atrás y sin romper modo detalle.
- Tests: cobertura >= 90% en el scope del módulo; incluye cursor y múltiples llamadas.
- Docs: `functions/users/README.md` y `README.md` raíz actualizados con ejemplos cURL y parámetros nuevos.


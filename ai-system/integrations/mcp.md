# MCP Inventory — Sport Monitor Cloud Functions

No hay MCP servers configurados para este proyecto actualmente.

---

## Estado actual

No se requieren MCPs en esta fase del proyecto. El backend opera con:
- Firebase Admin SDK (directo, sin MCP)
- Firebase CLI para deploys
- pytest para testing local

---

## Cuándo agregar MCPs

Re-ejecutar `/agents-creator` opción 7 (Update MCP inventory) cuando se integre:
- GitHub MCP para automatizar PRs/issues
- Slack MCP para notificaciones de deploy
- Database MCP para queries directas durante desarrollo

---

## Reglas de seguridad

- Nunca guardar API keys, tokens o secrets en archivos del repositorio.
- Documentar solo **nombres** de variables de entorno (e.g. `GITHUB_TOKEN`), nunca valores.
- Los secrets viven en la configuración del IDE o en variables de entorno del sistema.

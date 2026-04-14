# Hooks — Sport Monitor Cloud Functions

Hooks configurados en `.claude/settings.json`. Cada hook se ejecuta automáticamente en respuesta a un evento de sesión.

---

## Hooks activos

| Evento | Matcher | Comando | Rationale |
|--------|---------|---------|-----------|
| Stop | (ninguno) | Ejecutar `/skill_registry` al final de sesión si se añadió/modificó algún skill | Mantener `ai-system/skill-registry.md` actualizado |

---

## Detalle

### Stop → skill_registry auto-update

**Evento:** `Stop` (al finalizar la sesión de Claude Code)
**Condición:** Se ejecuta siempre; el skill internamente detecta si hay cambios en skills.
**Acción:** Regenera `ai-system/skill-registry.md` escaneando `ai-system/skills/*/SKILL.md`.
**Por qué:** Evita que el registro quede desactualizado después de agregar o modificar skills durante una sesión de trabajo.

---

## Cómo añadir un hook nuevo

1. Documentar aquí: evento, matcher, comando, rationale.
2. Añadir en `.claude/settings.json` bajo la clave `hooks`.
3. Verificar que no duplica un hook existente.

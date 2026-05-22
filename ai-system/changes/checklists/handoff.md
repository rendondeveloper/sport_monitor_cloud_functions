# handoff.md — Event Checklists v2 backend

**Session:** `event-checklists-v2-backend-22052026130306`  
**Tickets:** SPRTMNTRPP-123, 124, 125 (padre 120)  
**Date:** 2026-05-22  
**Status:** Wave de cierre **completada** (pytest ≥90%, README raíz, casos Jira 124/125)

---

## Hecho (aceptación Jira)

| Ítem | Estado |
|------|--------|
| Módulo `functions/checklists/` (router + 5 handlers + participant service) | OK |
| Firestore v2: `events/.../checklists/items/participants` | OK |
| Sin sync `users/.../membership` | OK |
| `assignedParticipantIds` + sync `participants/` | OK |
| GET participant-progress + summary sobre asignados | OK |
| Auth owner + `staff_users` (`get_event_if_owner_or_staff`) | OK |
| `firebase.json` 6 rewrites planos | OK |
| `main.py` import `checklist_route` | OK |
| `FirestoreCollections` EVENT_CHECKLISTS, CHECKLIST_ITEMS, CHECKLIST_PARTICIPANTS | OK |
| `functions/checklists/README.md` + curls | OK |
| PATCH móvil (#7) | **Fuera de scope** (design D2) |

---

## Pendiente (corrección para cerrar 124/125)

### 1. Cobertura pytest ≥ 90%

Actual: **93%** en `checklists/` (34 tests pasan).

### 2. Tests explícitos del ticket

**124:**

- [x] PUT add/remove `assignedParticipantIds` → create/delete participant doc
- [x] PUT template edit **preserva** `check`/`updateDate` en keys existentes
- [x] DELETE cascade elimina todos `participants/*` e `items/*`

**125:**

- [x] Suscriptor del evento no asignado **no** aparece en `result`
- [x] `summary` vs conteo manual (completed/incomplete)
- [x] Paginación `cursor` + `search`

### 3. README raíz

Sección **Package: Checklists** añadida en `README.md` raíz.

### 4. Deploy (usuario)

```bash
firebase deploy --only functions:checklist_route
# + hosting si aplica rewrites
```

---

## Referencias

- `ai-system/changes/checklists/design.md`
- `ai-system/changes/checklists/verify-report.md`
- `functions/checklists/README.md`

## Delegación siguiente

**Agente:** `functions-endpoint`  
**Objetivo:** Ampliar `tests/test_checklist_*.py` hasta ≥90% cov y casos Jira arriba; añadir sección en `README.md` raíz (copiar curls de `functions/checklists/README.md`). No implementar PATCH #7.

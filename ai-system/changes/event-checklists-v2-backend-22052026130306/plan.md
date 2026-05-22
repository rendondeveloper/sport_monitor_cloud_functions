# plan.md — Event Checklists v2 backend

`SDD: explore=req design=req verify=req tests=req docs=req — secuencia Jira 123→124→125, paths planos`

## Summary

Nuevo módulo `checklists/` en Cloud Functions: router `checklist_route` con **6 paths planos** (`/api/events/checklists/{action}`), Firestore v2 bajo `events/{eventId}/checklists/`, sync de `participants/` solo para asignados, y GET paginado de progreso. Auth CRM: creador del evento o staff.

## Impact

```
cross     : firestore_collections.py, event_owner_helper.py, main.py, firebase.json (6 rewrites)
endpoints : checklists/* (router + 5 handlers + participant service + progress)
tests     : tests/test_checklist_*.py (pytest >=90%)
docs      : checklists/README.md (curls per flat path)
sdd       : ai-system/changes/checklists/{explore,design}.md
```

## Waves

**W0** — Contract lock (123): `design.md` paths planos = canonical; optional Jira doc sync  
**W1 parallel** — cross: constants + staff auth helper + main + firebase.json · endpoint: CRUD 124  
**W2** — endpoint: `get_participant_progress` (125)  
**W3** — functions-test: pytest all handlers + router dispatch per flat path  
**W4** — functions-docs: README + curls  
**W5** — sdd-verify + qa-ready  

## Scope estimate

```
functions-cross   | +0 -4 files | Med | ~45m
functions-endpoint| +10 -0 files | High | ~3h
functions-test    | +6 -0 files | Med | ~2h
functions-docs    | +1 -0 files | Low | ~30m
TOTAL             | +17 -4      | —    | ~6h
```

## Skills

1. `/sdd_explore` → `ai-system/changes/checklists/explore.md`
2. `/sdd_design` → `ai-system/changes/checklists/design.md`
3. Wave 1–3 implementation → `backend_agent` / `functions-endpoint`
4. `/sdd_verify` → `verify-report.md`

## Path amendment

| Before (rejected) | After (canonical) |
|-------------------|-------------------|
| `GET /api/events/{eventId}/checklists` | `GET /api/events/checklists/list?eventId=` |
| `GET .../checklists/{checklistId}` | `GET /api/events/checklists/get?eventId=&checklistId=` |
| POST/PUT nested | `POST/PUT /api/events/checklists/create|update` + body ids |

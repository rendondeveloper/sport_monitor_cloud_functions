# verify-report.md — Event Checklists v2 backend

**Date:** 2026-05-22  
**Session:** `event-checklists-v2-backend-22052026130306`

## Checks

| Check | Status |
|-------|--------|
| Flat paths in `firebase.json` (6 rewrites) | OK |
| Router `checklist_route` dispatch | OK |
| `FirestoreCollections` constants | OK |
| Owner + staff auth helper | OK |
| CRUD + participant sync (124) | OK |
| participant-progress (125) | OK |
| PATCH mobile excluded | OK |
| README + curls | OK |
| pytest `test_checklist_*` (8 tests) | OK |

## Tests run

```bash
cd functions && python -m pytest tests/test_checklist_route.py tests/test_checklist_handlers.py -v
```

Result: **8 passed**

## Notes

- Deploy: `firebase deploy --only functions:checklist_route` (+ hosting rewrites if needed).
- Web (`sport_monitor_web` 126+) must use same flat paths in dart-define.

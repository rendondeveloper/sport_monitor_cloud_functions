# handoff.md — Event Checklists

**Status:** En curso — **Fix: participant-progress required por participante** (2026-05-28)

## Objective

Arreglar el cruce entre `participantIds` y `participants[]` para que en `participant-progress` se marque `isRequired` **por participante** correctamente (no “global”), usando el set de participantes del request para evaluar requeridos.

## Estado actual por wave

- **Wave 1 (código)**: **Completada** (fix implementado).
- **Wave 2 (tests)**: **Completada** (test agregado y pasó).
- **Wave 3 (docs)**: **En progreso** (actualizando documentación en README).

## Archivos realmente tocados

- `functions/checklists/checklist_common.py`
- `functions/checklists/get_participant_progress.py`
- `functions/tests/test_checklist_handlers.py`
- `functions/checklists/README.md`

## Siguiente

- Finalizar Wave 3: completar docs en README (y asegurar ejemplos/contrato actualizado para el fix).
- (Opcional) correr suite completa de tests para asegurar no-regresión.
- Queda listo para deploy.

## Referencias

- `ai-system/changes/checklists/design.md`

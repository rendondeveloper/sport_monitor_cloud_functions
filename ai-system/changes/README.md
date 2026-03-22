# Changes — Artefactos SDD por módulo

Directorio de artefactos generados durante el ciclo SDD (explore, design, verify).
Cada módulo tiene su propia carpeta con los artefactos de cada iteración.

## Layout

```
ai-system/changes/
├── README.md                     # Este archivo
│
├── competitors/                  # Artefactos del módulo competitors
│   ├── explore.md                # Output de /sdd_explore
│   ├── design.md                 # Output de /sdd_design
│   └── verify-report.md         # Output de /sdd_verify y /qa-ready
│
├── checkpoints/
│   ├── explore.md
│   ├── design.md
│   └── verify-report.md
│
├── events/
│   └── ...
│
└── <module>/
    ├── explore.md
    ├── design.md
    └── verify-report.md
```

## Cuándo se crean estos artefactos

| Archivo | Skill que lo crea | Cuándo |
|---------|------------------|--------|
| `explore.md` | `/sdd_explore` | Pre-implementación — módulo existente a extender |
| `design.md` | `/sdd_design` | Pre-implementación — diseño de contratos HTTP |
| `verify-report.md` | `/sdd_verify`, `/qa-ready` | Post-implementación, pre-deploy |

## Convenciones

- Los archivos son **append-only** — no borrar iteraciones anteriores
- Si hay múltiples features en el mismo módulo, añadir sección nueva en el mismo archivo
- Los `verify-report.md` incluyen la fecha para diferenciar iteraciones

## Relación con el workflow

```
/plan                          →  no genera archivo en changes/
/sdd_explore                   →  changes/<module>/explore.md
/sdd_design                    →  changes/<module>/design.md
Wave 1 + Wave 2                →  código en functions/
/sdd_verify + /qa-ready        →  changes/<module>/verify-report.md
Wave 3 (/update-readme)        →  functions/<module>/README.md (no en changes/)
```

## Ejemplo — flujo completo

```
1. Usuario: "Añadir endpoint para estadísticas de competidor"
2. /plan  → produce plan en la conversación (no en changes/)
3. /sdd_explore  → ai-system/changes/competitors/explore.md
4. /sdd_design   → ai-system/changes/competitors/design.md
5. Wave 1 implementa
6. Wave 2 tests
7. /sdd_verify   → ai-system/changes/competitors/verify-report.md
8. Wave 3 docs   → functions/competitors/README.md
9. /push         → commit en git
10. firebase deploy
```

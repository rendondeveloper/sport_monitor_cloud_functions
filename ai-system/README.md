# AI System — Sport Monitor Cloud Functions

Sistema de orquestación IA para el backend Python/Firebase (Cloud Functions 2nd Gen).

## Estructura

```
ai-system/
├── context/              # Conocimiento del proyecto
│   ├── architecture.md   # Patrones Firebase, respuestas HTTP, regiones
│   ├── coding-standards.md # Reglas obligatorias de código
│   ├── project-structure.md # Estructura functions/, módulos, helpers
│   └── workflow.md       # SDD fases, waves, phase decision table
├── agents/               # Sub-agentes especializados
│   ├── architect.md      # Coordinador (Opus)
│   ├── functions-cross.md # main.py, modelos, utils (Haiku)
│   ├── functions-endpoint.md # Endpoints HTTP (Haiku)
│   ├── functions-test.md # pytest tests (Sonnet)
│   └── functions-docs.md # README de módulos (Opus)
├── skills/               # Operaciones atómicas
│   ├── plan/
│   ├── sdd_explore/
│   ├── sdd_design/
│   ├── sdd_verify/
│   ├── new-function/
│   ├── add-model/
│   ├── add-util/
│   ├── add-firestore-query/
│   ├── add-test/
│   ├── qa-ready/
│   ├── push/
│   ├── update-readme/
│   └── skill_registry/
├── changes/              # Artefactos SDD por módulo
├── manifest.yaml
└── skill-registry.md
```

## Agentes

| Agent | Model | Responsabilidad |
|-------|-------|-----------------|
| architect | opus | Coordinador — planifica y delega, nunca escribe código |
| functions-cross | haiku | Registro en main.py, FirestoreCollections, modelos, utils |
| functions-endpoint | haiku | Implementación de endpoints HTTP con template obligatorio |
| functions-test | sonnet | pytest tests — unit + integration |
| functions-docs | opus | README de módulos |

## Skills

| Categoria | Skill | Descripcion |
|-----------|-------|-------------|
| Workflow | /plan | Analiza request y produce plan antes de escribir código |
| Workflow | /sdd_explore | Exploración pre-plan para módulos existentes |
| Workflow | /sdd_design | Diseño de contratos HTTP y Firestore paths |
| Workflow | /sdd_verify | Checklist post-implementación pre-deploy |
| Código | /new-function | Crea endpoint HTTP completo con template obligatorio |
| Código | /add-model | Añade modelo Firestore en models/ |
| Código | /add-util | Añade helper en utils/ |
| Código | /add-firestore-query | Añade query Firestore usando FirestoreHelper |
| Testing | /add-test | Añade pytest tests para función o helper |
| Testing | /qa-ready | Documento QA pre-deploy |
| Proceso | /push | Commit y push con Conventional Commits |
| Proceso | /update-readme | Crea o actualiza README de módulo |
| Proceso | /skill_registry | Regenera skill-registry.md |

## Wave execution

Todo cambio que involucre una nueva función sigue este orden:

```
Wave 1 (parallel): functions-cross + functions-endpoint
  └── functions-cross: registra en main.py, añade colecciones, modelos, utils
  └── functions-endpoint: implementa el handler HTTP con template obligatorio

Wave 2: functions-test
  └── tests/test_<module>_<function>.py, cobertura >= 90%

Wave 3: functions-docs  (SIEMPRE OBLIGATORIO — nunca omitir)
  └── Actualiza README del módulo afectado
```

## Reglas absolutas

1. `validate_request` + `verify_bearer_token` en TODA función
2. Respuestas exitosas: JSON directo — NUNCA wrappers `success`, `data`, `message`
3. Errores: solo código HTTP vacío — NUNCA JSON en errores (excepciones documentadas en architecture.md)
4. Early return — nunca anidar if/else para validaciones
5. `FirestoreCollections` para TODOS los nombres de colecciones
6. `FirestoreHelper` para TODO CRUD — nunca `firestore.client()` directo en endpoints

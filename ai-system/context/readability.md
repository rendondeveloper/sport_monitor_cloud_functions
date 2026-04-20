# Human Readability Standard (MANDATORY)

Objetivo: todo codigo debe ser facil de leer por humanos, explicito y mantenible.

## Principios

- Priorizar claridad sobre ingenio.
- Usar nombres descriptivos y semanticos.
- Mantener funciones cortas y de responsabilidad unica.
- Reducir anidacion con guard clauses y retornos tempranos.
- Evitar one-liners complejos y comportamiento implicito.
- Preferir pasos intermedios con variables bien nombradas.
- Comentar solo para explicar contexto o decisiones no obvias.

## Limites de complejidad

- Maximo 3 niveles de anidacion por bloque.
- Si una funcion no se puede explicar en 30 segundos, dividirla.
- El flujo principal debe entenderse en una sola lectura.

## Regla de decision

Si existen dos opciones validas, elegir la mas simple de entender.

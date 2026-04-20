# Regla de legibilidad (enforcement)

Aplica a todo codigo nuevo o modificado.

## Checklist obligatorio antes de cerrar una tarea

1. Los nombres explican intencion de negocio.
2. Se redujo complejidad accidental.
3. La anidacion se mantuvo al minimo posible.
4. La logica principal se puede seguir de forma lineal.
5. No se dejaron trucos innecesarios.
6. Los comentarios (si existen) explican contexto y decisiones.

## Anti-patrones

- Abreviaturas cripticas (`tmp2`, `procX`, `dataFn`).
- Funciones largas con multiples responsabilidades.
- Condicionales profundamente anidados.
- Expresiones densas en una sola linea.
- Side effects ocultos.

## Criterio de aceptacion

Un developer nuevo debe entender el flujo principal en menos de 5 minutos.

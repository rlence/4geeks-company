---
name: close-milestone
description: Cierra un hito del monorepo de forma consistente y verificable antes de abrir la PR.
---

# close-milestone

## Objetivo

Dejar un hito listo para PR: build/typecheck en verde, banco de memoria al día, y un commit que sigue el historial del repo — sin depender de que el desarrollador recuerde cada paso a mano.

## Inputs

- `hito`: identificador del hito (ej. `hito-4`).
- `paquetes_tocados`: lista de rutas dentro del monorepo modificadas en este hito (ej. `uis/website`, `uis/backoffice`).
- `rule_path`: ruta al archivo de reglas del hito en `context/rules/` (fuente del checklist de evaluación).

## Pasos

1. Por cada ruta en `paquetes_tocados`, ejecutar su `npm run build` (o `typecheck` si no hay build) y confirmar salida sin errores.
2. Releer `rule_path` y marcar contra el código qué ítems del checklist de evaluación están cubiertos; listar los que falten.
3. Actualizar `memory-bank/progress.md`: mover `hito` a "Completado" (o anotar qué queda pendiente) con la fecha del día.
4. Crear el commit siguiendo Conventional Commits, describiendo el hito cerrado.

## Criterios de aceptación (verificables)

- [ ] Cada ruta en `paquetes_tocados` compila/typechecka sin errores (evidencia: output del comando).
- [ ] `memory-bank/progress.md` tiene una entrada para `hito` con fecha de hoy.
- [ ] Ningún ítem del checklist de `rule_path` queda sin marcar y sin justificación explícita de exclusión.
- [ ] El commit generado sigue el formato Conventional Commits (`type: descripción`).

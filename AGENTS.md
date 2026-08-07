# AGENTS.md

Instrucciones para cualquier agente de código (Cursor, Windsurf, Claude Code…) que trabaje en este monorepo.

## Antes de empezar cualquier sesión

Lee, en este orden:

1. [`memory-bank/projectbrief.md`](memory-bank/projectbrief.md) — qué es Brasaland y qué problema resuelve este monorepo.
2. [`memory-bank/techContext.md`](memory-bank/techContext.md) — stack y restricciones técnicas vigentes.
3. [`memory-bank/progress.md`](memory-bank/progress.md) — qué está hecho y qué es lo siguiente.
4. [`CONTEXT.md`](CONTEXT.md) — contexto de negocio detallado del hito activo.
5. Las reglas relevantes en [`.agents/rules/`](.agents/rules/) para la carpeta que vas a tocar.

## Flujo obligatorio antes de cada commit

1. Confirmar que el cambio no toca una carpeta protegida (ver abajo) sin autorización explícita del desarrollador.
2. Implementar siguiendo las reglas aplicables de `.agents/rules/`.
3. Ejecutar build/typecheck del paquete o app tocada (`npm run build` / `npm run typecheck` según corresponda) — no se commitea con errores de tipos.
4. Verificar manualmente en el navegador (`npm run dev`) el flujo afectado — no basta con que compile.
5. Actualizar `memory-bank/progress.md` si el cambio mueve el estado de un hito (completa uno, empieza otro, deja algo pendiente).
6. Commit siguiendo Conventional Commits (`feat:`, `fix:`, `docs:`, …), un commit por unidad de trabajo coherente.

## Carpetas que no se modifican sin confirmación explícita del desarrollador

- `uis/talent-pipeline-tracker/` — Hito 3, ya entregado y evaluado.
- `packages/data-utils/` — Hito 2, ya entregado; otras apps lo **importan**, nunca lo copian ni lo modifican.
- `CONTEXT.md` — fuente de verdad de negocio; cambiarlo es una decisión del desarrollador, no del agente.
- Cualquier `.env*` — nunca se leen ni se commitean valores reales.

## Skills disponibles

- [`.agents/skills/close-milestone/`](.agents/skills/close-milestone/SKILL.md) — cierre consistente y verificable de un hito antes de abrir PR.

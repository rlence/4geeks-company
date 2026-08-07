# Progress — Monorepo Brasaland

| Hito | Estado | Fecha | Resumen |
|---|---|---|---|
| Hito 1 — Sitio web público | Completado | — | Landing pública + formulario "Brasa Points", migrado a Next.js en Hito 4 (antes HTML estático). |
| Hito 2 — Fundamentos de programación | Completado | — | Utilidades TypeScript puras de procesamiento de datos de Brasaland en `packages/data-utils` (filtrado, búsqueda, cálculos financieros, scoring, validaciones). |
| Hito 3 — Talent Pipeline Tracker | Completado | — | App Next.js en `uis/talent-pipeline-tracker` para gestionar candidaturas de selección de personal, consumiendo la API REST del curso. |
| Hito 4 — Ingeniería impulsada por IA | Completado | 2026-08-06 | Infraestructura de agentes (`memory-bank/`, `AGENTS.md`, `.agents/`) + migración de `uis/website` a Next.js + creación de `uis/backoffice` importando `packages/data-utils`. |

## Hito 4 — detalle de lo entregado

- `memory-bank/projectbrief.md`, `techContext.md`, `progress.md`.
- `AGENTS.md` raíz con flujo de 6 pasos antes de cada commit.
- `.agents/rules/monorepo-imports.md` (siempre activa) y `.agents/rules/frontend-fetch-pattern.md` (por patrón de archivo, `uis/**/*.tsx`).
- `.agents/skills/close-milestone/SKILL.md`.
- `uis/website`: migrado de HTML estático a Next.js + TypeScript, 9 componentes reutilizables, rutas `/` y `/brasa-points`. Build y lint en verde.
- `uis/backoffice`: nueva app Next.js, layout propio, `/` importa `packages/data-utils` (ranking de locaciones + top ítems vendidos) directamente desde su ubicación original. Build y lint en verde.

## Próximos pasos

- Abrir PR `milestone-4` → `main` con capturas de ambas apps y enlace a `AGENTS.md`.
- Futuros hitos: `services/` (API centralizada FastAPI, aún no creada), y las funcionalidades de Operaciones/Formación descritas en `projectbrief.md`.

# Progress — Monorepo Brasaland

| Hito | Estado | Fecha | Resumen |
|---|---|---|---|
| Hito 1 — Sitio web público | Completado | — | Landing pública + formulario "Brasa Points", migrado a Next.js en Hito 4 (antes HTML estático). |
| Hito 2 — Fundamentos de programación | Completado | — | Utilidades TypeScript puras de procesamiento de datos de Brasaland en `packages/data-utils` (filtrado, búsqueda, cálculos financieros, scoring, validaciones). |
| Hito 3 — Talent Pipeline Tracker | Completado | — | App Next.js en `uis/talent-pipeline-tracker` para gestionar candidaturas de selección de personal, consumiendo la API REST del curso. |
| Hito 4 — Ingeniería impulsada por IA | Completado | 2026-08-06 | Infraestructura de agentes (`memory-bank/`, `AGENTS.md`, `.agents/`) + migración de `uis/website` a Next.js + creación de `uis/backoffice` importando `packages/data-utils`. |
| Project 1 — Directorio de Proveedores | Completado | 2026-08-07 | Primer backend real del monorepo: API FastAPI + TinyDB + Pydantic en `services/api` para el directorio de proveedores de Compras y Proveedores, más página `/suppliers` en `uis/backoffice`. |

## Project 1 — detalle de lo entregado

- `services/api`: FastAPI + TinyDB + Pydantic, empaquetado con `uv` (`uv sync`, `uv run seed`, `uv run uvicorn main:app`). 6 endpoints (`POST/GET/GET-by-id/PATCH rate/PATCH status/DELETE /suppliers`), validación cruzada `country`/`currency` y de `categories`/`rate_per_unit` con 422, `seed.py` con los 15 proveedores literales de `CONTEXT.md` (idempotente). CORS habilitado para `http://localhost:3000`.
- `uis/backoffice/src/app/suppliers`: listado con filtros por país/categoría en la URL (sin recarga), alta de proveedor con validación cliente + manejo de error 422 de la API, edición de tarifa y toggle activo/suspendido con badge visual, todo con estado de fetch explícito y `AbortController` (`.agents/rules/frontend-fetch-pattern.md`).
- `CONTEXT.md` raíz reemplazado por el briefing del Milestone 09 (Directorio de Proveedores).
- Verificado end-to-end con Playwright headless (filtro por URL, alta de proveedor, toggle de estado) además de `uv run seed` + Swagger. Build y lint de `uis/backoffice` en verde.

## Hito 4 — detalle de lo entregado

- `memory-bank/projectbrief.md`, `techContext.md`, `progress.md`.
- `AGENTS.md` raíz con flujo de 6 pasos antes de cada commit.
- `.agents/rules/monorepo-imports.md` (siempre activa) y `.agents/rules/frontend-fetch-pattern.md` (por patrón de archivo, `uis/**/*.tsx`).
- `.agents/skills/close-milestone/SKILL.md`.
- `uis/website`: migrado de HTML estático a Next.js + TypeScript, 9 componentes reutilizables, rutas `/` y `/brasa-points`. Build y lint en verde.
- `uis/backoffice`: nueva app Next.js, layout propio, `/` importa `packages/data-utils` (ranking de locaciones + top ítems vendidos) directamente desde su ubicación original. Build y lint en verde.

## Próximos pasos

- Abrir PR `project-1-supplier-directory` → `main` con capturas de `uv run seed`, un endpoint filtrado en Swagger y el listado del frontend con filtro aplicado.
- Futuros proyectos: el resto de las funcionalidades de Operaciones/Formación descritas en `projectbrief.md`, ahora con `services/api` ya como precedente de backend real en el monorepo.

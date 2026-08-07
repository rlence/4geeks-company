# Regla: patrón de fetch en el frontend

**Alcance:** por patrón de archivo — `uis/**/*.tsx`, excepto `uis/talent-pipeline-tracker/**` (ya entregado y congelado, es la referencia de esta regla, no un objetivo de aplicarla de nuevo).

## Regla

Toda llamada a una API externa dentro de un componente cliente debe exponer un estado explícito de tres valores (`"loading" | "success" | "error"`) y cancelar la petición con `AbortController` en el cleanup de su `useEffect`. No se usan librerías de gestión de estado externas (Redux, Zustand, Jotai) en ninguna app de `uis/`.

Esta regla es solo para **datos que vienen de una API por red**. Lógica síncrona en memoria (por ejemplo, funciones puras importadas de `packages/data-utils`) no necesita estado de fetch ni `useEffect` — puede llamarse directamente en un Server Component.

## Por qué

Es el patrón que ya se validó y evaluó en `uis/talent-pipeline-tracker` (Hito 3): sin él, cambiar de filtro rápido puede pintar una respuesta de red vieja después de la nueva, y sin estados explícitos de carga/error la UI no cumple los criterios de evaluación de esa app. Mantenerlo consistente en toda la capa `uis/` evita que cada app nueva reinvente su propio manejo de estado de red.

## Referencia de implementación

`uis/talent-pipeline-tracker/src/hooks/useCandidates.ts` — hook que combina `useSearchParams`, `fetch` y `AbortController` con el estado de tres valores.

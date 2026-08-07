# Brasaland — Backoffice

Panel interno de Brasaland Digital. Creado en el Hito 4 como la app donde vivirá la lógica interna de la empresa (autenticación, gestión operativa, comunicación interna, etc. en próximos hitos).

## Qué muestra hoy

La ruta `/` importa las utilidades de `packages/data-utils` (Hito 2) directamente desde su ubicación original en el monorepo — **no se copia código** — y renderiza en pantalla:

- Ranking de las 14 ubicaciones de Brasaland por performance (`rankLocationsByPerformance`).
- Top 3 de ítems más vendidos (`findTopSellingItems`).

Ambas funciones son síncronas y en memoria (operan sobre los datos de ejemplo de `packages/data-utils/src/data/sampleData.ts`), así que se llaman directamente en un Server Component — sin estado de fetch ni `useEffect`.

## Por qué `experimental.externalDir`

`packages/data-utils` vive fuera de este directorio de proyecto y el monorepo no tiene un workspace configurado en la raíz que resuelva ese import de otra forma. `next.config.ts` activa `experimental.externalDir: true` para permitir que Next.js compile el `.ts` fuente de `packages/data-utils` tal como está, sin necesidad de copiarlo ni de convertir el repo a un workspace de npm.

## Stack

- Next.js (App Router) + TypeScript.
- Tailwind CSS (vía el scaffold).

## Cómo levantarlo

```bash
cd uis/backoffice
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000).

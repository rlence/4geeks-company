# @repo/data-utils

Utilidades TypeScript **puras** de procesamiento de datos para las operaciones de Brasaland — Hito 2: Fundamentos de Programación. Sin backend, sin IA, sin persistencia: todo opera en memoria sobre los datos de ejemplo de `src/data/sampleData.ts`.

Ver el contexto completo del hito en [`CONTEXT.md`](../../CONTEXT.md) (raíz del repo).

## Stack

- TypeScript en modo estricto (`strict`, `noUncheckedIndexedAccess`), sin `any`.
- Todas las funciones exportadas son **arrow functions puras** (`export const fn = (...) => {...}`): no mutan sus parámetros, no dependen de variables globales.
- Módulos ESM nativos (`"type": "module"`, `moduleResolution: NodeNext`) — los imports relativos usan extensión `.js` apuntando a los `.ts`, por lo que el mismo código compilado corre igual en Node y en el navegador sin bundler.

## Comandos

```bash
npm install          # instala typescript, tsx y http-server como devDependencies
npm run typecheck     # npx tsc --noEmit — valida tipos sin generar archivos
npm run demo          # npx tsx src/demo.ts — ejecuta todas las funciones sobre los datos de ejemplo
npm run build         # npx tsc — compila src/ a dist/ (necesario para servir index.html)
npm run serve         # npx http-server . -p 3000 -a 0.0.0.0 — sirve el paquete completo
```

Para probar la página manual: `npm run build && npm run serve`, luego abrir `http://localhost:3000/src/index.html`.

## Estructura

```
src/
├── types/models.ts          # Interfaces y type aliases: MenuItem, SaleTransaction, Location, WasteRecord, CountryMetrics...
├── data/sampleData.ts       # Datos de ejemplo (menú, locaciones, ventas, desperdicio)
├── utils/
│   ├── format.ts            # Helpers compartidos: round2, tasa USD/COP, comparación de fechas
│   ├── collections.ts       # Filtrado y ordenamiento (no mutan el array original)
│   ├── search.ts            # Búsqueda lineal (findLocationById, findMenuItemByName) y binaria (binarySearchLocationByCapacity)
│   ├── transformations.ts   # Cálculos financieros, scoring de performance, agregaciones y reportes
│   └── validations.ts       # Reglas de negocio de MenuItem, SaleTransaction y Location (acumulan todos los errores)
├── demo.ts                  # Smoke test ejecutable: llama cada función pública e imprime el resultado
├── browser.ts                # Handlers de los botones de index.html
└── index.html                # Página de prueba manual con Tailwind (vía CDN)
```

## Notas de diseño

- **Fechas**: no hay timezone por locación en este modelo simplificado, así que las comparaciones de fecha (`filterSalesByDateRange`, `calculateDailyRevenue`) usan el calendario local (`getFullYear/getMonth/getDate`), no timestamps exactos.
- **Moneda**: los datos de ejemplo ya traen `USD` y `COP` precalculados en cada `Price`; las funciones financieras leen el campo de la moneda pedida directamente. `convertCurrency` es una utilidad genérica independiente (tasa fija 1 USD = 4000 COP).
- **Validaciones**: cada validador retorna **todos** los errores encontrados, no solo el primero.

Detalle completo de fórmulas y decisiones de diseño en el plan de este hito (`context/plans/hito2.md`, fuera de este repositorio).

# Tech Context — Monorepo Brasaland

## Estructura del monorepo

Layers según [`README.md`](../README.md) raíz:

| Carpeta | Contiene |
|---|---|
| `uis/` | Frontends (`website` público, `backoffice` interno, `talent-pipeline-tracker`) |
| `services/` | API centralizada FastAPI (aún no creada) |
| `data/` | Raw / pipelines / process / eval |
| `agents/`, `skills/`, `mcps/` | Agentes e integraciones de **producto** (no confundir con `.agents/`) |
| `packages/`, `shared/` | Código reutilizable entre proyectos (`data-utils`, tipos compartidos) |
| `infra/`, `scripts/`, `internal/` | Docker, deploys, CLIs internas |

No hay workspace runner configurado en la raíz (sin `npm workspaces` ni `turborepo`) — cada app/paquete en `uis/`/`packages/` tiene su propio `package.json` y se instala/corre de forma independiente.

## Apps y paquetes existentes

- **`packages/data-utils`** (Hito 2): TypeScript ESM puro (`"type": "module"`, `moduleResolution: NodeNext`). Sin backend, sin persistencia — todo opera en memoria sobre `src/data/sampleData.ts`. Los imports internos usan extensión `.js` apuntando a `.ts` (patrón NodeNext). **No tiene `dist/` commiteado** (está en `.gitignore`) — cualquier consumidor debe importar el `.ts` fuente, no un build.
- **`uis/talent-pipeline-tracker`** (Hito 3, entregado — no modificar sin confirmación): Next.js App Router + TypeScript + Tailwind, consume la API REST del curso (`playground.4geeks.com/tracker/api/v1`). Fija el patrón de referencia para toda futura app en `uis/`: sin librerías de estado externas (Redux/Zustand/Jotai), estado de fetch explícito `"loading" | "success" | "error"`, `AbortController` en cada `useEffect` de fetch, filtros en la URL vía `useSearchParams`.
- **`uis/website`** (Hito 1 → migrado en Hito 4): landing pública + formulario de fidelización "Brasa Points". Antes de Hito 4 era HTML estático + Tailwind CDN + JS vanilla; a partir de Hito 4 es Next.js + TypeScript con componentes reutilizables.
- **`uis/backoffice`** (nueva en Hito 4): app interna, layout propio, importa `packages/data-utils` para mostrar resultados de la lógica de negocio de Hito 2 en pantalla.

## Convenciones de scaffold

Next.js App Router, TypeScript, Tailwind, ESLint — scaffolded siempre con:

```bash
npx create-next-app@latest <nombre> --typescript --app --tailwind --eslint
```

`npm` como package manager en todo el repo.

## Restricciones vigentes

- Variables de entorno sensibles van en `.env.local` (nunca commiteado) + `.env.example` documentando la variable sin valor real.
- Ningún paquete/app de un hito ya entregado se copia a otro lugar — se importa desde su ubicación original (ver [`.agents/rules/monorepo-imports.md`](../.agents/rules/monorepo-imports.md)).
- `uis/backoffice` importa `packages/data-utils` fuera de su propio directorio de proyecto Next.js — requiere `experimental.externalDir: true` en su `next.config.ts`, ya que no hay workspace configurado que resuelva ese import de otra forma. **Verificado en Hito 4**: `experimental.externalDir` solo funciona de forma confiable con el compilador **webpack** de Next.js — Turbopack (default desde Next 16) no resuelve módulos fuera del proyecto de la misma forma. Además, como `packages/data-utils` usa resolución NodeNext (imports internos con extensión `.js` apuntando a `.ts`), hace falta `config.resolve.extensionAlias = { ".js": [".ts", ".tsx", ".js"] }` en la función `webpack()` de `next.config.ts` para que esos imports internos se resuelvan. Por eso los scripts `dev`/`build` de `uis/backoffice` fuerzan `--webpack` explícitamente.

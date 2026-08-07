# Tech Context — Monorepo Brasaland

## Estructura del monorepo

Layers según [`README.md`](../README.md) raíz:

| Carpeta | Contiene |
|---|---|
| `uis/` | Frontends (`website` público, `backoffice` interno, `talent-pipeline-tracker`) |
| `services/` | Backends (`services/api`: FastAPI + TinyDB del Directorio de Proveedores) |
| `data/` | Raw / pipelines / process / eval |
| `agents/`, `skills/`, `mcps/` | Agentes e integraciones de **producto** (no confundir con `.agents/`) |
| `packages/`, `shared/` | Código reutilizable entre proyectos (`data-utils`, tipos compartidos) |
| `infra/`, `scripts/`, `internal/` | Docker, deploys, CLIs internas |

No hay workspace runner configurado en la raíz (sin `npm workspaces` ni `turborepo`) — cada app/paquete en `uis/`/`packages/` tiene su propio `package.json` y se instala/corre de forma independiente.

## Apps y paquetes existentes

- **`packages/data-utils`** (Hito 2): TypeScript ESM puro (`"type": "module"`, `moduleResolution: NodeNext`). Sin backend, sin persistencia — todo opera en memoria sobre `src/data/sampleData.ts`. Los imports internos usan extensión `.js` apuntando a `.ts` (patrón NodeNext). **No tiene `dist/` commiteado** (está en `.gitignore`) — cualquier consumidor debe importar el `.ts` fuente, no un build.
- **`uis/talent-pipeline-tracker`** (Hito 3, entregado — no modificar sin confirmación): Next.js App Router + TypeScript + Tailwind, consume la API REST del curso (`playground.4geeks.com/tracker/api/v1`). Fija el patrón de referencia para toda futura app en `uis/`: sin librerías de estado externas (Redux/Zustand/Jotai), estado de fetch explícito `"loading" | "success" | "error"`, `AbortController` en cada `useEffect` de fetch, filtros en la URL vía `useSearchParams`.
- **`uis/website`** (Hito 1 → migrado en Hito 4): landing pública + formulario de fidelización "Brasa Points". Antes de Hito 4 era HTML estático + Tailwind CDN + JS vanilla; a partir de Hito 4 es Next.js + TypeScript con componentes reutilizables.
- **`uis/backoffice`** (Hito 4, extendida en Project 1): app interna, layout propio, importa `packages/data-utils` en `/` y consume `services/api` en `/suppliers` (directorio de proveedores).
- **`services/api`** (Project 1, extendido en Project 2): primer backend Python del monorepo. FastAPI + TinyDB (`db.json`, gitignored — se regenera con `uv run seed`) + Pydantic v2, gestionado con `uv`. Estructura flat (`main.py`, `models.py`, `database.py`, `seed.py`, `config.py`, `auth.py`, `mail.py`, `routes/suppliers.py`, `routes/auth.py`) — no un layout `src/<paquete>`.

## Autenticación (Project 2 — AUTH-03)

- `services/api` tiene ahora un sistema mínimo de auth: `users_table` (TinyDB), password hasheado con `bcrypt`, sesión vía JWT (`pyjwt`, `HS256`, 24h) creado en `POST /auth/login`. La dependencia `get_current_user` (`auth.py`) lee el header `Authorization: Bearer <token>` y protege `POST /auth/change-password`.
- Restablecimiento de contraseña (`forgot-password` / `reset-password`): token opaco (`secrets.token_urlsafe`), guardado **hasheado** (`sha256`) en `password_reset_tokens_table` junto con `expires_at` (30 min) y `used`. No es JWT — la invalidación tras un solo uso es trivial con TinyDB y no requiere una blocklist.
- Envío de email: **Resend**, vía `httpx` directo a su API REST (`mail.py`), sin SDK. Requiere `RESEND_API_KEY` en `services/api/.env` (gitignored) — la cuenta gratuita/trial de Resend solo permite enviar a la dirección con la que te registraste, salvo que verifiques un dominio propio.
- `services/api/.env` (nuevo, antes el servicio no tenía secretos): `JWT_SECRET_KEY`, `ACCESS_TOKEN_TTL_MINUTES`, `RESET_TOKEN_TTL_MINUTES`, `FRONTEND_URL`, `RESEND_API_KEY`, `EMAIL_FROM`. Cargado con `python-dotenv` en `config.py`.
- Frontend: sesión guardada en `localStorage` (`uis/backoffice/src/lib/session.ts`) — no hay cookie httpOnly ni servidor de sesiones en ningún otro punto del monorepo, se mantiene la misma simplicidad.
- No existe `POST /auth/register` ni página de registro: los usuarios se seedean (`seed.py`, `USERS_SEED`) igual que los proveedores de Project 1.

## `uv run seed` sin layout `src/` (Project 1)

`uv_build` (el backend por defecto de `uv init`) espera un único módulo o paquete en `src/<nombre>/`, incompatible con la estructura plana que pide el rule del proyecto (`main.py`, `models.py`, etc. directamente en `services/api/`). Se resolvió cambiando el `build-system` a **hatchling** con `[tool.hatch.build.targets.wheel] only-include = [...]` listando los archivos/carpetas sueltos — así `[project.scripts] seed = "seed:main"` se instala igual y `uv run seed` funciona sin mover nada a `src/`. `tool.uv.package` debe quedar en `true` (o simplemente no declararse) para que `uv sync` instale los entry points; con `package = false` uv los omite en silencio (solo un warning).

## Convenciones de scaffold

Next.js App Router, TypeScript, Tailwind, ESLint — scaffolded siempre con:

```bash
npx create-next-app@latest <nombre> --typescript --app --tailwind --eslint
```

`npm` como package manager en todo el repo.

## Restricciones vigentes

- Variables de entorno sensibles van en `.env.local` (nunca commiteado) + `.env.example` documentando la variable sin valor real.
- Cualquier app de `uis/` que consuma un backend propio (no una API mock externa) necesita `CORSMiddleware` en ese backend con el origin exacto del dev server (`http://localhost:3000`) — sin esto, el `fetch` del navegador falla con "Failed to fetch" aunque `curl` a la misma URL funcione (bloqueo de CORS, no un problema de red). Ver `services/api/main.py`.
- Ningún paquete/app de un hito ya entregado se copia a otro lugar — se importa desde su ubicación original (ver [`.agents/rules/monorepo-imports.md`](../.agents/rules/monorepo-imports.md)).
- `uis/backoffice` importa `packages/data-utils` fuera de su propio directorio de proyecto Next.js — requiere `experimental.externalDir: true` en su `next.config.ts`, ya que no hay workspace configurado que resuelva ese import de otra forma. **Verificado en Hito 4**: `experimental.externalDir` solo funciona de forma confiable con el compilador **webpack** de Next.js — Turbopack (default desde Next 16) no resuelve módulos fuera del proyecto de la misma forma. Además, como `packages/data-utils` usa resolución NodeNext (imports internos con extensión `.js` apuntando a `.ts`), hace falta `config.resolve.extensionAlias = { ".js": [".ts", ".tsx", ".js"] }` en la función `webpack()` de `next.config.ts` para que esos imports internos se resuelvan. Por eso los scripts `dev`/`build` de `uis/backoffice` fuerzan `--webpack` explícitamente.

# TESTING.md — API de autenticación + backoffice (Brasaland)

Ticket: **AUTH-088** (obligatorio) + **API-042** (extra, backoffice/suppliers). El plan completo con el razonamiento detrás de cada decisión vive en [`context/plans/project-3.md`](../../../context/plans/project-3.md).

## Cómo ejecutar

### Backend — pytest

```bash
cd services/api
uv sync
uv run pytest                     # toda la suite
uv run pytest --cov=auth --cov=routes --cov-report=term-missing   # con cobertura
```

No hace falta ningún setup adicional: `tests/conftest.py` redirige `DB_PATH` a un archivo temporal antes de importar la app (nunca toca `db.json`) y fija valores dummy de `JWT_SECRET_KEY`/`RESEND_API_KEY` si no están ya en el entorno, así que corre igual en local o en CI sin `.env` real.

### Frontend — Jest

```bash
cd uis/backoffice
npm install
npx jest --coverage
# o: npm run test:coverage
```

Independiente del backend: no necesita la API corriendo ni variables de entorno.

## Qué cubre cada suite

### `services/api/tests/` (pytest)

| Módulo | Qué prueba | Tipo de casos |
|---|---|---|
| `test_auth_helpers.py` | `auth.py`: hashing (`hash_password`/`verify_password`), JWT (`create_access_token`/`decode_access_token`), resolución de usuario autenticado (`get_current_user`) — lógica pura, sin pasar por HTTP | feliz, límite, fallo |
| `test_login.py` | `POST /auth/login` | feliz, límite, fallo |
| `test_forgot_password.py` | `POST /auth/forgot-password` (con `send_password_reset_email` mockeado — no llama a Resend real) | feliz, límite, fallo |
| `test_reset_password.py` | `POST /auth/reset-password` | feliz, límite, fallo |
| `test_change_password.py` | `POST /auth/change-password` | feliz, límite, fallo |
| `test_suppliers_crud.py` *(extra, API-042)* | `routes/suppliers.py`, grupo CRUD/listado: `create`, `list`, `get`, `delete` | feliz, límite, fallo |
| `test_suppliers_management.py` *(extra, API-042)* | `routes/suppliers.py`, grupo de gestión operativa: `update_rate`, `update_status` | feliz, límite, fallo |

### `uis/backoffice/src/lib/__tests__/` (Jest)

| Módulo | Qué prueba | Tipo de casos |
|---|---|---|
| `session.test.ts` | `lib/session.ts`: `getToken`/`setToken`/`clearToken` (almacenamiento del token de sesión) | feliz, fallo |
| `authApi.test.ts` | `lib/authApi.ts`: `getApiErrorMessage` | feliz, límite, fallo |
| `suppliersApi.test.ts` | `lib/suppliersApi.ts`: `getApiErrorMessage` (copia duplicada de la de `authApi.ts`, ver hallazgos) | feliz, fallo |

Estas mismas suites de Jest cubren tanto el requisito de TS de AUTH-088 ("si tu proyecto incluye lógica de utilidades en TypeScript") como la actividad extra **FE-019** ("≥3 funciones de utilidad") — hay 4 funciones cubiertas (`getToken`, `setToken`, `clearToken`, `getApiErrorMessage`), así que no se duplicó trabajo.

## Alcance y decisiones (por qué estos casos y no otros)

- **No existe `POST /auth/register`** ni un endpoint `/auth/token` separado — es una decisión de alcance ya tomada en el hito anterior (usuarios seedeados, ver `memory-bank/progress.md`). No se testea lo que no existe; en su lugar, `test_auth_helpers.py` cubre directamente la lógica de emisión/validación de tokens.
- **`suppliers` es el único dominio de recursos del backoffice** hoy. El ticket API-042 pide "dos grupos de endpoints distintos" asumiendo varios dominios (recursos, usuarios, elementos) que no existen en este repo. Se dividió `routes/suppliers.py` en dos *grupos funcionales* reales — CRUD/listado vs. gestión operativa (tarifa/estado) — en vez de inventar un segundo dominio de negocio.
- **No se prueba serialización HTTP ni internals del framework**: los tests de FastAPI usan `TestClient` para ejercitar el flujo real (necesario para JWT/sesión), pero cada aserción es sobre una decisión de negocio (¿se concede el token?, ¿se rechaza el password?, ¿se invalida el token de reset ya usado?), no sobre cómo FastAPI serializa el JSON. Los tests de `getApiErrorMessage` en Jest deliberadamente **no** tocan `fetch`/`request()` — esa función queda fuera de alcance por ser justamente la capa de serialización HTTP.
- **Aislamiento de base de datos**: se modificó `database.py` para leer `DB_PATH` de una variable de entorno (con el mismo default de siempre si no está seteada). `tests/conftest.py` la redirige a un archivo temporal antes de importar la app, así los tests nunca leen ni escriben en `db.json` (que además tiene datos de desarrollo reales y está gitignored).

## Bugs y comportamientos detectados vía IA durante el testing

Se le pidió a la IA que, endpoint por endpoint, señalara casos límite no obvios (campos vacíos, reutilización de tokens, inputs en los bordes de la validación). De ahí salieron estos hallazgos, documentados con un test explícito en vez de "arreglados" en silencio:

1. **`hash_password` revienta con `ValueError` sin controlar para passwords de más de 72 bytes** (límite físico de bcrypt) — `test_auth_helpers.py::TestHashPassword::test_password_longer_than_72_bytes_raises_value_error`. Hoy esto se traduciría en un `500` si un usuario mandara un password larguísimo en vez de un `422` legible. No se corrigió (cambiar el comportamiento de un endpoint público es una decisión de producto), pero queda documentado y cubierto para que no pase desapercibido.
2. **`ForgotPasswordRequest.email` es `str`, no `EmailStr`** — no se valida el formato del email a nivel de modelo. No rompe nada porque el endpoint no distingue emails inexistentes de mal formados (mismo `200 {}` genérico), pero es un gap de validación de entrada.
3. **`routes/suppliers.py` no tiene ninguna dependencia de autenticación** — a diferencia de `change-password`, cualquiera puede crear/editar/borrar proveedores sin sesión. Fuera de alcance de este ticket arreglarlo, pero es un hallazgo real que vale la pena escalar.
4. **`change-password` permite reusar el mismo password actual** como `new_password` — no hay validación que lo impida (`test_change_password.py::test_reusing_the_same_password_is_currently_allowed`).
5. **`getApiErrorMessage` y la clase `ApiError` están duplicadas byte a byte** entre `lib/authApi.ts` y `lib/suppliersApi.ts`. Ambas copias están testeadas por separado (`authApi.test.ts`, `suppliersApi.test.ts`) precisamente para que la duplicación quede visible; es candidata a extraerse a un módulo compartido en un ticket futuro.

## Resultados de cobertura

**pytest** (`uv run pytest --cov=auth --cov=routes --cov-report=term-missing`):

```
Name                  Stmts   Miss  Cover   Missing
---------------------------------------------------
auth.py                  32      0   100%
routes/__init__.py        0      0   100%
routes/auth.py           54      0   100%
routes/suppliers.py      54      0   100%
---------------------------------------------------
TOTAL                   140      0   100%
52 passed
```

100% en `auth.py` + `routes/auth.py` (mínimo pedido: 70%) y 100% en `routes/suppliers.py` (mínimo pedido para la actividad extra: 60%).

**Jest** (`npx jest --coverage`):

```
File             | % Stmts | % Branch | % Funcs | % Lines
-----------------|---------|----------|---------|--------
session.ts       |   91.66 |       50 |     100 |    100
authApi.ts       |   57.14 |    33.33 |    37.5 |     50
suppliersApi.ts  |   47.61 |    18.18 |      25 |  45.16
9 passed, 3 test suites
```

`authApi.ts` y `suppliersApi.ts` no llegan a un % alto porque el reporte de cobertura cuenta también la función `request()` (fetch + manejo de headers/status) y los wrappers de cada llamada a la API (`login`, `createSupplier`, etc.) — esa es justamente la capa de serialización HTTP que el ticket pide **no** testear. La lógica de negocio real de esos archivos (`getApiErrorMessage`) está al 100% cubierta caso por caso. `session.ts` sí refleja cobertura real de sus 3 funciones (la única línea sin cubrir es la rama de SSR de `getToken`, no testeable en jsdom — ver comentario en `session.test.ts`).

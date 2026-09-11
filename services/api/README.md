# API — Brasaland

API FastAPI + TinyDB + Pydantic de Brasaland: directorio de proveedores de Compras y Proveedores, y autenticación de usuarios (login, recuperación y cambio de contraseña).

Modelo de datos, categorías válidas, estados válidos y datos semilla del directorio de proveedores: ver [`CONTEXT.md`](../../CONTEXT.md) en la raíz del monorepo.

## Cómo correrlo

```bash
cd services/api
cp .env.example .env  # completa JWT_SECRET_KEY, RESEND_API_KEY y SUPABASE_* (ver abajo)
uv sync                # instala dependencias
uv run seed             # siembra los 15 proveedores y 2 usuarios de prueba (idempotente)
uv run uvicorn main:app --reload --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`.

## Variables de entorno (`.env`, nunca commiteado — ver `.env.example`)

| Variable | Descripción |
|---|---|
| `JWT_SECRET_KEY` | Clave de firma de los tokens de sesión (JWT). Genera una aleatoria propia, no reutilices la de ejemplo. |
| `ACCESS_TOKEN_TTL_MINUTES` | Expiración del token de sesión (login). Default `1440` (24h). |
| `RESET_TOKEN_TTL_MINUTES` | Expiración del token de restablecimiento de contraseña. Default `30`. |
| `FRONTEND_URL` | Origen del frontend, usado para construir el enlace `{FRONTEND_URL}/reset-password?token=...` del email. |
| `RESEND_API_KEY` | API key de [Resend](https://resend.com) (Dashboard → API Keys). En la cuenta gratuita/trial solo se puede enviar a la dirección con la que te registraste, salvo que verifiques un dominio propio. |
| `EMAIL_FROM` | Remitente del email de restablecimiento. Default `Brasaland <onboarding@resend.dev>` (funciona en dev sin dominio propio). |
| `SUPABASE_URL` | URL del proyecto Supabase (Project Settings → API) donde vive `telemetry_events`. Crea el proyecto y corre `sql/telemetry_events.sql` en el SQL Editor antes de arrancar la API. |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave `service_role` (no `anon`) del mismo proyecto — la API inserta sin pasar por un usuario de Supabase Auth. |

## Estructura

```
main.py           # instancia FastAPI, monta los routers de proveedores, auth y telemetría
models.py         # modelos Pydantic (proveedores + auth + telemetría) + enums de dominio
database.py       # instancia única de TinyDB (db.json, generado, no se commitea)
config.py         # carga .env (python-dotenv), expone la config de auth/email/supabase
supabase_client.py # factory del cliente supabase-py (inyectable, mockeable en tests)
auth.py           # hashing de password (bcrypt), JWT de sesión, dependencia get_current_user
mail.py           # envío del email de restablecimiento vía Resend (httpx, sin SDK)
routes/
  suppliers.py    # los 6 endpoints del directorio
  auth.py         # login, forgot-password, reset-password, change-password
  telemetry.py    # POST /telemetry/events (upsert en Supabase) + GET /telemetry/report (cache 60s)
sql/
  telemetry_events.sql # DDL de la tabla telemetry_events, correr a mano en Supabase
seed.py           # SUPPLIERS_SEED + USERS_SEED, siembra idempotente

../telemetry/
  analysis.py     # pipeline Pandas del reporte técnico — sibling de api/, importado por
                   # routes/telemetry.py vía sys.path (no es un paquete uv instalable, ver
                   # context/plans/project-6.3-telemetria.md Decisión 1)

../reporting/
  endpoints.py    # los 3 endpoints del Pipeline de Desempeño de Negocio (Hito 6 Parte 2),
                   # importado por main.py vía sys.path — mismo mecanismo que ../telemetry/

../../data/pipelines/
  pipeline.py     # flow de Prefect (extract → transform → load), corre con el venv de este
                   # servicio (`cd services/api && uv run python ../../data/pipelines/pipeline.py`)
  sql/reporting_schema.sql # DDL de reporting.weekly_location_performance + reporting.pipeline_runs
../../data/process/
  weekly_aggregation.py    # transformación pura (Pandas, sin Prefect), testeada aparte
```

## Notas de negocio — Proveedores

- `country` y `currency` deben ser consistentes (Colombia→COP, USA→USD); combinaciones inconsistentes se rechazan con 422.
- `DELETE /suppliers/{id}` existe para corregir datos erróneos — en la operativa real los proveedores se **suspenden**, no se eliminan (`PATCH /suppliers/{id}/status`).

## Notas de negocio — Autenticación

- `POST /auth/login` — `{ email, password }` → `{ access_token, token_type }`. `401` si las credenciales no coinciden (mensaje genérico, no distingue email inexistente de password incorrecta).
- `POST /auth/forgot-password` — `{ email }` → siempre `200`, nunca revela si el email existe. Si existe, genera un token de un solo uso (expira en `RESET_TOKEN_TTL_MINUTES`) y envía el enlace de restablecimiento por email.
- `POST /auth/reset-password` — `{ token, new_password }` → `400` si el token es inválido, ya usado o expiró; en éxito actualiza la contraseña e invalida el token.
- `POST /auth/change-password` — requiere `Authorization: Bearer <access_token>`. `{ current_password, new_password }` → `400` si `current_password` no coincide.
- No hay `POST /auth/register` ni página de registro — los usuarios se seedean (`USERS_SEED` en `seed.py`), igual que los proveedores. Usuarios de prueba: `felipe.guerrero@brasaland.com` / `jake.morrison@brasaland.com`, password `brasaland2026`.

## Notas de negocio — Telemetría

- `POST /telemetry/events` — `{ events: [...] }` → `{ received, stored, rejected }`. Cada evento se valida contra el envelope `TelemetryEvent`; los inválidos no cancelan el lote. Upsert por `event_id` (no `insert`): reintentos del frontend con el mismo lote no duplican filas.
- `GET /telemetry/report` — reporte técnico (no de negocio): volumen por día/tipo, tasa de error diaria, latencia p95 por endpoint por día, y tasa de fallos de login. Query params opcionales `start_date`/`end_date` (ISO 8601); por defecto, últimos 7 días. Cache en memoria de 60s por combinación de fechas — no recalcula en cada request.

## Notas de negocio — Pipeline de Desempeño de Negocio (Hito 6, Parte 2)

- `GET /reporting/pipeline-runs/latest` — estado/metadata de la corrida más reciente de `weekly_location_performance_flow` (`reporting.pipeline_runs`).
- `POST /reporting/pipeline-runs?week_start=<opcional ISO date>` — dispara el flow real (importado desde `data/pipelines/pipeline.py`, no reimplementado). Sin `week_start`, calcula la semana ISO anterior a hoy.
- `GET /reporting/weekly-location-performance?week_start=<opcional>` — filas de `reporting.weekly_location_performance` para esa semana; sin `week_start`, la más reciente con datos.
- Requiere el schema `reporting` creado (`data/pipelines/sql/reporting_schema.sql`) **y** agregado a Project Settings → API → Exposed schemas en Supabase — PostgREST no sirve schemas fuera de `public` por defecto.
- `country` viaja en `inbound_order_created`/`outbound_order_created`/`stock_waste_registered`/`stock_threshold_triggered` desde `Ingredient.country` (ya existía en el frontend). `unit_cost` es un input real y requerido en `InboundOrderForm` y en `OutboundOrderForm` cuando el motivo es `waste` — sin él no se puede calcular `total_purchase_cost`/`total_waste_cost`.
- El pipeline no toca `services/telemetry/analysis.py` ni `GET /telemetry/report` — lee `telemetry_events` en modo solo lectura.

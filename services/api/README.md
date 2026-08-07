# API — Brasaland

API FastAPI + TinyDB + Pydantic de Brasaland: directorio de proveedores de Compras y Proveedores, y autenticación de usuarios (login, recuperación y cambio de contraseña).

Modelo de datos, categorías válidas, estados válidos y datos semilla del directorio de proveedores: ver [`CONTEXT.md`](../../CONTEXT.md) en la raíz del monorepo.

## Cómo correrlo

```bash
cd services/api
cp .env.example .env  # completa JWT_SECRET_KEY y RESEND_API_KEY (ver abajo)
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

## Estructura

```
main.py           # instancia FastAPI, monta los routers de proveedores y auth
models.py         # modelos Pydantic (proveedores + auth) + enums de dominio
database.py       # instancia única de TinyDB (db.json, generado, no se commitea)
config.py         # carga .env (python-dotenv), expone la config de auth/email
auth.py           # hashing de password (bcrypt), JWT de sesión, dependencia get_current_user
mail.py           # envío del email de restablecimiento vía Resend (httpx, sin SDK)
routes/
  suppliers.py    # los 6 endpoints del directorio
  auth.py         # login, forgot-password, reset-password, change-password
seed.py           # SUPPLIERS_SEED + USERS_SEED, siembra idempotente
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

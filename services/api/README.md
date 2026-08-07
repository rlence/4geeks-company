# Directorio de Proveedores — API

API FastAPI + TinyDB + Pydantic para el directorio de proveedores de Compras y Proveedores (Brasaland). Reemplaza la hoja de cálculo que hoy gestiona Lucía Fernández por una única fuente de verdad accesible desde `uis/backoffice`.

Modelo de datos, categorías válidas, estados válidos y datos semilla: ver [`CONTEXT.md`](../../CONTEXT.md) en la raíz del monorepo.

## Cómo correrlo

```bash
cd services/api
uv sync              # instala dependencias
uv run seed          # siembra los 15 proveedores iniciales (idempotente)
uv run uvicorn main:app --reload --port 8000
```

Swagger UI: `http://127.0.0.1:8000/docs`.

## Estructura

```
main.py           # instancia FastAPI, monta el router de proveedores
models.py         # modelos Pydantic (SupplierCreate, SupplierOut, updates) + enums de dominio
database.py       # instancia única de TinyDB (db.json, generado, no se commitea)
routes/
  suppliers.py    # los 6 endpoints del directorio
seed.py           # SUPPLIERS_SEED (dataset literal del CONTEXT) + siembra idempotente
```

## Notas de negocio

- `country` y `currency` deben ser consistentes (Colombia→COP, USA→USD); combinaciones inconsistentes se rechazan con 422.
- `DELETE /suppliers/{id}` existe para corregir datos erróneos — en la operativa real los proveedores se **suspenden**, no se eliminan (`PATCH /suppliers/{id}/status`).

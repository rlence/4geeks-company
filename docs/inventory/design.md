# API de inventario — Project 8, dependencia

Implementa las seis rutas de Hito 5 sobre PostgreSQL, mediante SQLModel. El frontend conserva sus arrays y ahora dispone de detalle por ingrediente y refresco de saldo tras registrar movimientos. El stock es global por ingrediente, no por local.

## Arquitectura y contratos

`routes/inventory.py` valida autenticación/capacidades y adapta HTTP. `inventory/schemas.py` valida entradas y serializa decimales como números JSON. `repository.py` agrega entradas y salidas por separado; `service.py` controla transacciones y salidas. `models.py` mapea las tablas, pero no crea el esquema al arrancar.

| Ruta | Método | Éxito |
| --- | --- | --- |
| `/inventory/products` | GET | Array de ingredientes con `current_stock`; filtro opcional `country` |
| `/inventory/products` | POST | 201, ingrediente con saldo cero |
| `/inventory/products/{id}` | GET | Ingrediente con saldo |
| `/inventory/orders/inbound` | POST | 201, entrada |
| `/inventory/orders/outbound` | POST | 201, salida |
| `/inventory/orders` | GET | Array combinado, ordenado por fecha, tipo e ID |

No se actualiza directamente el stock ni se borran movimientos. Se calcula entradas menos salidas. Cada movimiento bloquea primero la fila del ingrediente; una salida calcula el saldo en una sentencia posterior al bloqueo dentro de READ COMMITTED. La transacción confirma saldo y movimiento conjuntamente. El rol de aplicación puede insertar y consultar, pero no borrar. El permiso UPDATE(id) permite bloquear ingredientes y una política RLS con CHECK false impide modificar su identidad.

La API es la única escritora prevista. Los accesos administrativos no deben insertar movimientos eludiendo este protocolo. Una futura integración con otros escritores requerirá preservar esta regla.

Cantidades: decimal positivo finito, hasta 12 dígitos enteros y 6 decimales. PostgreSQL usa `NUMERIC(18,6)` y el cálculo usa Decimal. La respuesta es número JSON por compatibilidad con el cliente, con las limitaciones de representación de JavaScript. Los IDs se limitan al entero seguro de JavaScript. SKU único y campos/enums de Brasaland según el contexto.

## Permisos e identidad

Todos los endpoints requieren JWT del login actual. `user_uuid` conserva el nombre académico, pero contiene `str(user.doc_id)` de TinyDB, no un UUID real. Se rechaza con 403 un cuerpo que atribuya el movimiento a otra identidad.

`inventory_permissions` en el registro TinyDB guarda las capacidades asignadas administrativamente. No existe una ruta pública para editar ese campo. Si se define `INVENTORY_PERMISSIONS`, su objeto JSON reemplaza esas asignaciones, incluso si es `{}`. Sin asignación se deniega acceso. Ejemplo exclusivamente ilustrativo, a sustituir por IDs de usuarios existentes:

```text
{"ID_OPERADOR":["inventory:read","inventory:write"],"ID_LECTOR":["inventory:read"]}
```

La escritura exige ambas capacidades. Los permisos abarcan ambos países; el filtro de país no es autorización. No reiniciar/reutilizar los IDs de TinyDB cuando existan movimientos persistidos. La identidad MCP deberá tener solo lectura; OAuth y el mapeo de scopes se implementan en Project 8.

## Configuración y arranque

La configuración del entorno tiene prioridad, seguida del `.env` del servicio y del `.env` raíz como valores por defecto. Los scripts de preparación usan la misma prioridad. No se guardan secretos en Git.

| Variable | Propósito |
| --- | --- |
| `INVENTORY_ADMIN_DATABASE_URL` | Solo preparación/migración, conexión PostgreSQL administrativa |
| `INVENTORY_DATABASE_URL` | Conexión PostgreSQL de `inventory_app`; la API rechaza usuarios administradores |
| `INVENTORY_PERMISSIONS` | Mapa de capacidades por ID TinyDB |
| `NEXT_PUBLIC_INVENTORY_API_URL` | Dirección pública de FastAPI, nunca una credencial |

Usar una conexión PostgreSQL de Supabase, por ejemplo Session pooler para IPv4. En pooler el usuario limitado es `inventory_app.<project-ref>`; en conexión directa es `inventory_app`. Mantener host, puerto y base de datos del panel Connect. Codificar caracteres reservados de la contraseña en la URL (`@` se convierte en `%40`). Se exige TLS para servidores remotos. No reutilizar la API key de Supabase como contraseña PostgreSQL.

La migración canónica es `supabase/migrations/20261002012816_inventory_api.sql`, creada con la CLI de Supabase. Se almacena ahí en vez de `services/api/sql/inventory/` para conservar una sola fuente versionada. Crea un esquema privado, tablas, índices, RLS y rol NOLOGIN. No altera tablas anteriores.

Desde la raíz del repositorio:

```bash
uv sync --project services/api
# Solo en un entorno donde la migración NO se haya aplicado:
uv run --project services/api python scripts/setup_inventory.py --apply
# Solicita una contraseña nueva por entrada oculta para el rol limitado:
uv run --project services/api python scripts/setup_inventory.py --enable-login
```

Después configurar `INVENTORY_DATABASE_URL` con el usuario limitado y la contraseña elegida, y asignar capacidades explícitas. `--enable-login` cambia la contraseña de inventory_app: usarlo para su preparación, no como rutina de arranque. También se puede establecer desde el editor SQL de Supabase; no cambia la contraseña del administrador.

```bash
# Reemplazar ID_OPERADOR por el ID autorizado:
uv run --project services/api python scripts/seed_inventory.py --owner-id ID_OPERADOR --development
# Desde services/api:
uv run uvicorn main:app --reload --port 8000
```

La semilla verifica usuario y permisos, prepara seis ingredientes, cuatro entradas y tres salidas (una merma) y registra su versión en una transacción. Un bloqueo de semilla evita duplicación concurrente. Repetirla no repite movimientos. Los SKU existentes incompatibles detienen el proceso sin sobrescribirlos.

Sin conexión o con configuración de permisos inválida, inventario devuelve 503; no impide arrancar las demás rutas. Sin capacidades asignadas devuelve 403.

## Errores y límites

400 saldo insuficiente con el mensaje literal de Hito 5; 401 sesión inválida; 403 permiso o identidad inválida; 404 ingrediente ausente; 409 SKU duplicado; 422 entrada inválida; 503 persistencia indisponible. Los errores de dominio incluyen `detail` y `code`. Los de validación conservan el formato FastAPI.

Logs de inventario: método, plantilla de ruta, ID de usuario validado, HTTP status e identificador UUID de petición. `X-Request-Id` permite correlacionar respuesta y logs. No se registran tokens ni cadenas de conexión.

Conexión acotada a 5 s, adquisición del pool a 5 s, bloqueo a 3 s y sentencias a 5 s. Son límites por fase; no prometen un plazo total de 5 s. MCP debe incorporar su presupuesto total. No hay reintentos automáticos de escrituras: una desconexión durante commit puede dejar resultado incierto; consultar antes de repetir.

## Validación

Pruebas de contratos, permisos y API en `test_inventory.py`; integración y concurrencia PostgreSQL en `test_inventory_postgres.py`. Esta última exige un cluster local aislado en puerto 55439, crea una base aleatoria y elimina solo esa base al terminar. No apuntarla a desarrollo o producción. Pruebas con mocks no acreditan concurrencia.

```bash
# INVENTORY_TEST_ADMIN_URL debe apuntar al cluster aislado local:55439/postgres.
uv run --project services/api python -m pytest services/api/tests tests/pipelines -q
npm --prefix uis/backoffice test -- --runInBand
npm --prefix uis/backoffice run build
npm --prefix uis/backoffice run lint
```

La suite comprueba saldo fraccional, agregación sin multiplicación de JOINs, rollback, reapertura de conexiones, semilla repetible y dos salidas simultáneas de 7 con saldo 10 (201 y 400; saldo final 3). Reabrir conexiones no equivale a una prueba completa de reinicio de toda la aplicación: comprobar también ese flujo al validar desarrollo.

## Estado de esta ejecución

- Rama `feature/project-8-inventory-api`, basada en Project 7 Parte 2 ya integrado.
- 195 pruebas backend/pipelines pasaron, incluidas siete PostgreSQL reales locales. Avisos heredados: clave corta de un test JWT y logging de Prefect al cerrar su servidor temporal.
- 16 pruebas frontend pasaron. Build correcto; lint sin errores y un aviso existente en un archivo generado de coverage.
- Migración aplicada en el proyecto Supabase configurado. Conexión administrativa comprobada; cuatro tablas con RLS; anon/authenticated/service_role sin acceso al esquema; inventory_app con lectura y sin borrado.
- Pendiente: contraseña/login y conexión de inventory_app, asignación explícita de usuarios, semilla y flujo real completo en Supabase con la identidad de aplicación. No se ha asignado escritura a usuarios por defecto.
- La comprobación de navegador la realiza el usuario, por preferencia explícita. No se declara ejecutada ni se ha creado commit/PR.

Pasos manuales: iniciar sesión con operador; abrir inventario y detalle; registrar entrada, consumo y merma; comprobar saldo e historial; recargar/reiniciar API y comprobar persistencia; intentar salida excesiva; verificar que el usuario lector recibe 403 al intentar escribir. Confirmar identidad de lectura MCP cuando se implemente Project 8.

### Asignaciones autorizadas

Felipe (ID 1), Jake (ID 2) y Ricardo (ID 3) tienen lectura y escritura de inventario en la base local, por autorización del usuario. Son asignaciones locales, no valores predeterminados de nuevos usuarios ni privilegios de Supabase. Reiniciar/resembrar TinyDB puede eliminarlas.

## Actualización: conexión existente autorizada

Por petición explícita del usuario, si no se configura `INVENTORY_DATABASE_URL`, la API reutiliza `INVENTORY_ADMIN_DATABASE_URL`. La conexión dedicada conserva prioridad y su validación del usuario inventory_app. Esta excepción permite ejecutar el entorno de desarrollo con su conexión existente, sin modificar contraseñas ni archivos .env. Los permisos de usuario del backend siguen activos; el acceso PostgreSQL de esta alternativa tiene privilegios administrativos. Antes de desplegar, configurar la conexión dedicada y retirar la credencial administrativa del entorno de ejecución.

Semilla aplicada con el usuario local ID 3 autorizado: seis ingredientes y siete movimientos. 25 pruebas focalizadas del módulo pasan. Las notas anteriores sobre conexión y semilla pendientes describen el estado previo a esta actualización.

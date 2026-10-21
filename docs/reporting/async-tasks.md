# Proyecto 10 — Reporte semanal mediante Celery

`POST /reporting/pipeline-runs` publica `reporting.weekly_report` con una sola cadena `week_start`. Devuelve `202 Accepted`, `{"task_id":"..."}` y `Location: /tasks/<id>`. El worker invoca el flow existente de Prefect; el job nocturno sigue usando su CLI. `GET /tasks/<id>` consulta el resultado de Celery y solo expone `week_start` y `records_loaded` en éxito.

## Preparación

1. Aplicar `services/api/sql/task_dead_letters.sql` a la base de Supabase usada por el worker. Solo `service_role` puede leer/escribir esa tabla. `reporting.pipeline_runs` y `reporting.weekly_location_performance` deben existir como antes.
2. Configurar `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `REDIS_URL` en el entorno de ejecución, sin poner secretos en el frontend. En Compose, `REDIS_URL=redis://redis:6379/0` se configura para API, worker y Flower. Fuera de Compose, el default de desarrollo es `redis://localhost:6379/0`.
3. Ejecutar `docker compose up --build -d redis worker flower api`. Flower: `http://localhost:5555` (solo loopback). Para parar el trabajador sin parar la API: `docker compose stop worker`; para retomarlo: `docker compose up -d worker`.
4. Comprobar el registro con `docker compose exec worker celery --app=celery_app:app inspect registered` y el broker con `docker compose exec redis redis-cli ping`. No poner Flower sin protección en una interfaz pública.

Para una prueba del transporte sin tocar datos de negocio, ejecutar desde el host con el venv de la API: `cd services/api && uv run python -c 'from celery_app import app; print(app.send_task("reporting.queue_probe").get(timeout=10))'`. Debe devolver `{'ok': True}`.

Redis usa volumen y AOF; `noeviction` impide expulsar mensajes al llenarse la memoria, pero hace fallar escrituras. AOF con sincronización por defecto no elimina toda ventana de pérdida ante caída brusca. El productor devuelve `503` si no puede reservar el ID o publicar; nunca ejecuta el flow como fallback dentro de FastAPI.

## Contrato y estados

```bash
curl -i -X POST 'http://localhost:8000/reporting/pipeline-runs?week_start=2026-10-19'
curl -i 'http://localhost:8000/tasks/<task_id>'
```

La fecha debe ser un lunes ISO; sin parámetro se fija el lunes de la semana anterior en UTC. Un UUID mal formado devuelve `422`; un ID no aceptado o caducado, `404`. Celery llama `PENDING` incluso a IDs que no conoce, por eso la API guarda un marcador temporal en Redis para los IDs que publica. `STARTED` requiere `task_track_started=True`. `RETRY` se proyecta como `pending` con `retrying: true`; no se confunde con `FAILURE` terminal. Los resultados y marcadores expiran tras 48 horas. El resultado fallido no publica el mensaje de excepción en HTTP.

El objetivo de menos de 200 ms corresponde al `POST` **con Redis sano**. No espera el worker ni el resultado. Bajo caída del broker devuelve `503` tras los límites de conexión configurados. `task_acks_late=True` y `task_reject_on_worker_lost=True` favorecen la redelivery tras pérdida del worker, por lo que el procesamiento debe tolerar duplicados; el KPI semanal se carga por upsert `(location_id, week_start)`.

## Reintentos y DLQ

La tarea permite hasta **tres reintentos** después del intento inicial, con esperas exponenciales de 1, 2 y 4 segundos. Prefect puede reintentar sus propias tareas dentro de una ejecución del flow; los reintentos de Celery vuelven a ejecutar el flow completo y pueden crear varias filas en `reporting.pipeline_runs`. El resultado final del reporte se sobrescribe por upsert. La tarea tiene límite blando de 55 minutos y duro de 60; la visibilidad del broker es de 120 minutos.

En el fallo final, `public.task_dead_letters` guarda `task_id`, semana, intento, error acotado y estado de publicación. Después Celery envía **solo el `task_id`** a la cola Redis `dead_letter`, que el worker normal no consume. Flower muestra tareas Celery y workers; la tabla y la cola terminal se inspeccionan por separado. Para ver el número de mensajes: `docker compose exec redis redis-cli LLEN dead_letter`. No usar `LPOP` ni purgar la cola para una mera inspección.

Si la base aceptó el registro pero Redis falló al publicar, el registro queda `pending`. Tras restaurar el broker, ejecutar `docker compose exec worker python /app/scripts/reconcile_dead_letters.py`. Este comando republica hasta 100 pendientes y marca cada uno como `published`. PostgreSQL y Redis no comparten transacción: ante un corte justo después de publicar pueden quedar dos mensajes con el mismo ID lógico. La tabla impone unicidad por `task_id`; investigar antes de reenviar manualmente. No hay consumidor automático de la DLQ.

Cada intento escribe `task_id`, número de intento, estado, duración y error en el log del worker. El error para BD se limita a 500 caracteres y se redactan valores conocidos de URL/clave; un traceback solo queda en logs internos. No enviar capturas con secretos ni eventos reales.

## Verificación

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_reporting_endpoints.py services/api/tests/test_async_tasks.py services/api/tests/test_dead_letters.py -q
services/api/.venv/bin/python -m pytest services/api/tests/test_pipeline_flow.py -q
docker compose config --quiet
```

Para una comprobación de extremo a extremo, arrancar los servicios, publicar una semana válida y observar `pending → started → success` en `GET` y Flower, además de la fila de `reporting.pipeline_runs`. Inducir un fallo controlado en un entorno de prueba para observar backoff, `failure`, fila `task_dead_letters` y mensaje en `dead_letter`; no usar datos de producción para esa demostración. Detener API con una tarea ya encolada y confirmar que el worker sigue ejecutándola. Medir varias publicaciones con broker sano y registrar p95 del `POST`.

El endpoint manual conserva el acceso previo; antes de exponerlo fuera de un entorno controlado se debe decidir autenticación/autorización y un límite de disparos. Flower también debe permanecer restringido a desarrollo o protegido.

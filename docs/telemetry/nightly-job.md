# Proyecto 9 — Exportación nocturna de telemetría

`scripts/nightly_export.py` corre fuera de FastAPI. Cada ejecución toma el día calendario anterior en UTC o el valor de `TARGET_DATE=YYYY-MM-DD`, guarda un CSV de auditoría y llama al pipeline semanal existente como subproceso. El CSV **no** alimenta el pipeline: ambos leen `public.telemetry_events` en Supabase. `public.job_runs` registra la orquestación; `reporting.pipeline_runs`, el ETL de Prefect.

## Instalación

1. Aplicar `services/api/sql/job_runs.sql` en Supabase SQL Editor. Ese SQL crea tabla, índices parciales, RLS y las RPC `claim_nightly_job`, `heartbeat_nightly_job`, `finish_nightly_job`. Conceder su ejecución solo al `service_role` del servidor. Comprobar que los roles `anon` y `authenticated` no pueden leer ni reservar.
2. Configurar `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` en el entorno **del job**; el pipeline usa los mismos valores. Mantener la clave fuera del frontend y del repositorio.
3. Probar desde la raíz del monorepo con el venv que ya incluye `supabase` y `prefect`:

   ```bash
   TARGET_DATE=2026-10-20 services/api/.venv/bin/python scripts/nightly_export.py
   ```

   Una fecha futura válida también se acepta para pruebas; probablemente produce un CSV con cabecera y cero filas. Evitar usarla contra el entorno real, pues `completed` impedirá otra corrida de esa fecha.

4. Probar el contenedor de una sola ejecución:

   ```bash
   docker compose run --build --rm nightly-job
   ```

   `data/raw/` está montado desde el host para conservar el CSV tras eliminar el contenedor. El servicio `nightly-job` está bajo el perfil `jobs`, por lo que `docker compose up` habitual no lo mantiene corriendo.

5. Instalar `infra/cron/nightly_export.crontab.example` con el usuario autorizado a ejecutar Docker, sustituyendo la ruta absoluta del checkout. La expresión `15 1 * * *` dispara a las **01:15 de la zona horaria del host cron**. Configurar ese host en UTC para que el horario sea 01:15 UTC. El programa calcula «ayer» en UTC incluso si el host tiene otra zona, pero esa otra zona desplazaría la hora de disparo. Verificar el crontab instalado con `crontab -l` y revisar la primera corrida.

Se eligió crontab del sistema más un contenedor de trabajo de una sola ejecución. Así el disparador queda fuera de FastAPI y no requiere añadir un scheduler al proceso API. La imagen comparte el entorno Python del pipeline y termina al concluir el trabajo.

## Estados, reintentos y recuperación

La RPC de reserva crea `pending` y transiciona a `processing` en una misma transacción. Un índice único parcial permite **un solo** `processing` por `job_name`; otro impide dos `completed` para la misma fecha. Si existe una corrida `completed` para el día, el script sale sin exportar ni lanzar el pipeline. Si hay otra instancia en `processing`, sale silenciosamente con log `INFO`.

El proceso actualiza `heartbeat_at` durante la exportación y mientras espera al subproceso. Ante error ordinario, marca `failed`, conserva un CSV ya terminado y devuelve código no cero. Un retry de ese día puede reutilizar ese CSV y relanzar solo el pipeline. El CSV se escribe en un temporal y se publica con reemplazo atómico; un fallo antes de publicar no deja un archivo final parcial.

Una muerte brusca del proceso no ejecuta `finally`. Al siguiente disparo, la RPC marca `failed` un `processing` cuyo heartbeat supere dos horas y permite una nueva reserva. Esto **no** es una reparación instantánea: hasta el siguiente disparo o una ejecución manual, la fila antigua seguirá en `processing`. Investigar un lock antiguo antes de repetir manualmente si puede existir un trabajador todavía vivo. La ejecución del pipeline tiene un timeout de una hora y el proceso hijo se termina si se pierde la reserva.

Si `job_runs` dice `completed` pero falta su CSV, el script devuelve error y no relanza el ETL. Se debe investigar el volumen y restaurar el backup por procedimiento operativo. Los CSV pueden contener `user_id`, `session_id` y propiedades de eventos: el archivo se crea con permisos privados, queda ignorado por Git y no se copia a logs ni a PRs.

## Día exportado frente a semana calculada

Para `TARGET_DATE=2026-10-20`, el CSV contiene eventos del intervalo `[2026-10-20T00:00Z, 2026-10-21T00:00Z)`. El subproceso ejecuta `data/pipelines/pipeline.py --week-start 2026-10-19 --triggered-by schedule`: recalcula la semana ISO que contiene ese día desde la base de datos y hace upsert en `reporting.weekly_location_performance`. De lunes a sábado, ese reporte semanal es provisional. La corrida posterior al domingo recalcula la semana completa. Un evento tardío puede cambiar el reporte de la semana sin modificar el CSV ya exportado; ese CSV sigue siendo un snapshot del momento de su exportación.

## Observabilidad

Cada log propio del job incluye timestamp, nombre, fecha objetivo y estado. Revisar la última fila de `public.job_runs` para `nightly_export`, además de `reporting.pipeline_runs` para la corrida interna. Ejemplos **sintéticos**:

La salida estándar del subproceso se descarta para no mezclar trazas de Prefect con el log de control ni copiar payloads accidentalmente. Ante fallo, `job_runs.error_message` registra la clase y el motivo saneado; `reporting.pipeline_runs` conserva el diagnóstico interno del ETL.

```text
2026-10-21 01:15:00Z INFO job=nightly_export target_date=2026-10-20 status=processing started run_id=<uuid>
2026-10-21 01:15:03Z INFO job=nightly_export target_date=2026-10-20 status=processing csv_exported rows=2
2026-10-21 01:15:17Z INFO job=nightly_export target_date=2026-10-20 status=completed finished run_id=<uuid>
2026-10-21 01:20:00Z INFO job=nightly_export target_date=2026-10-20 status=already_completed skipped
2026-10-22 01:15:17Z ERROR job=nightly_export target_date=2026-10-21 status=failed RuntimeError: pipeline exited with code 1
```

Ejemplo **sintético y redactado** del CSV:

```csv
event_id,timestamp,session_id,user_id,event_type,schema_version,request_id,tags
<uuid>,2026-10-20T08:00:00+00:00,<session>,,api_request,1,,"{""country"": ""CO""}"
```

Las líneas de log no copian eventos ni secretos. Vigilar también la **ausencia** de corridas: si el cron deja de disparar, no habrá errores nuevos que consultar. Un monitor operativo debe alertar si la última ejecución es más antigua que un ciclo.

## Validación reproducible

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_nightly_export.py -q
services/api/.venv/bin/python -m pytest services/api/tests/test_pipeline_flow.py services/api/tests/test_reporting_endpoints.py services/api/tests/test_telemetry.py -q
docker compose config --quiet
```

La carrera real se comprueba con `tests/pipelines/test_nightly_job_sql.py` contra un PostgreSQL temporal local, después de aplicar el DDL. La variable `NIGHTLY_TEST_POSTGRES_DSN` debe apuntar a un socket bajo `/tmp` o `/private/tmp`; la prueba trunca `job_runs` y no admite una base remota. Los tests con fakes cubren Python, pero no prueban la exclusión transaccional.

Para el PR: documentar `15 1 * * *` en host UTC, los logs sintéticos de éxito/fallo/omisión, el ejemplo redactado del CSV y la etiqueta `cronjob`. Antes de activar cron en un entorno real, aplicar el SQL y confirmar permisos y volumen persistente allí.

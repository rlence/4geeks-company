-- Tabla de almacenamiento real de telemetría (Project 6.2).
-- Correr manualmente en el SQL Editor de Supabase. No hay tooling de
-- migraciones en este repo todavía; este archivo es la fuente de verdad
-- del esquema hasta que exista uno.
--
-- Contrato: 1:1 con TelemetryEvent (services/api/models.py) — sin columna
-- "service" (no existe en el envelope aprobado de Brasaland).
-- Append-only: no hay UPDATE/DELETE en el código de la app.

create table telemetry_events (
  event_id uuid primary key,
  timestamp timestamptz not null,
  session_id uuid not null,
  user_id text,
  event_type text not null,
  schema_version text not null,
  request_id text,
  tags jsonb not null default '{}'::jsonb
);

create index idx_telemetry_events_timestamp on telemetry_events (timestamp);
create index idx_telemetry_events_event_type on telemetry_events (event_type);
create index idx_telemetry_events_tags on telemetry_events using gin (tags);

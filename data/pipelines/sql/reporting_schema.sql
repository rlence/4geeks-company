-- Esquema `reporting` — destino del pipeline de Desempeño de Negocio
-- (Hito 6, Parte 2). Correr manualmente en el SQL Editor de Supabase.
-- No hay tooling de migraciones en este repo todavía; este archivo es
-- la fuente de verdad del esquema hasta que exista uno.
--
-- Después de correr esto: agregar "reporting" en Project Settings → API
-- → Exposed schemas — PostgREST no sirve schemas fuera de "public" por
-- defecto, sin esto cualquier query devuelve 404 aunque la tabla exista.

create schema if not exists reporting;

create table reporting.weekly_location_performance (
  id uuid primary key default gen_random_uuid(),
  location_id text not null,
  country text not null,
  week_start date not null,
  total_purchase_cost numeric not null default 0,
  total_waste_cost numeric not null default 0,
  waste_ratio numeric not null default 0,
  stockout_events_count integer not null default 0,
  price_alert_events_count integer not null default 0,
  currency text not null,
  computed_at timestamptz not null default now(),
  unique (location_id, week_start)
);

create table reporting.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  pipeline_name text not null default 'weekly_location_performance',
  week_start date not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,              -- 'running' | 'completed' | 'failed'
  records_extracted integer,
  records_loaded integer,
  error_message text,
  triggered_by text not null         -- 'schedule' | 'manual'
);

-- Exponer un schema en Project Settings → API no le da permisos a los
-- roles de PostgREST — hace falta este GRANT explícito, si no cualquier
-- query devuelve 403 "permission denied for schema reporting".
grant usage on schema reporting to anon, authenticated, service_role;
grant all on all tables in schema reporting to anon, authenticated, service_role;
grant all on all sequences in schema reporting to anon, authenticated, service_role;
alter default privileges in schema reporting grant all on tables to anon, authenticated, service_role;
alter default privileges in schema reporting grant all on sequences to anon, authenticated, service_role;

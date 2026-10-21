-- Proyecto 9: orquestación nocturna. Aplicar en Supabase SQL Editor.
-- El status processing es el único lock; los índices hacen cumplir la
-- exclusión incluso cuando dos clientes intentan reservar al mismo tiempo.

create table if not exists public.job_runs (
  id uuid primary key default gen_random_uuid(),
  job_name text not null,
  target_date date not null,
  status text not null check (status in ('pending', 'processing', 'completed', 'failed')),
  created_at timestamptz not null default now(),
  started_at timestamptz,
  heartbeat_at timestamptz,
  finished_at timestamptz,
  error_message text,
  check (error_message is null or length(error_message) <= 500)
);

create index if not exists job_runs_name_date_idx
  on public.job_runs (job_name, target_date);
create unique index if not exists job_runs_one_processing_idx
  on public.job_runs (job_name) where status = 'processing';
create unique index if not exists job_runs_one_completed_day_idx
  on public.job_runs (job_name, target_date) where status = 'completed';
-- Cubre la carrera donde otra instancia completa el mismo día entre el
-- SELECT inicial y el paso pending -> processing de esta reserva.
create unique index if not exists job_runs_one_active_or_completed_day_idx
  on public.job_runs (job_name, target_date)
  where status in ('processing', 'completed');

alter table public.job_runs enable row level security;
revoke all on public.job_runs from anon, authenticated;
grant select, insert, update on public.job_runs to service_role;

-- Una llamada RPC es una transacción: ningún cliente ve la fila pending
-- intermedia. El índice parcial resuelve la carrera que un SELECT no resuelve.
create or replace function public.claim_nightly_job(
  p_job_name text, p_target_date date, p_stale_after_seconds integer default 7200
) returns table(outcome text, run_id uuid)
language plpgsql security invoker set search_path = '' as $$
declare v_id uuid;
begin
  if p_job_name <> 'nightly_export' or p_target_date is null
     or p_stale_after_seconds < 60 then
    raise exception 'invalid nightly job claim';
  end if;

  update public.job_runs
     set status = 'failed', finished_at = now(),
         error_message = 'stale_run_recovered'
   where job_name = p_job_name and status = 'processing'
     and coalesce(heartbeat_at, started_at, created_at)
         < now() - make_interval(secs => p_stale_after_seconds);

  if exists (select 1 from public.job_runs
             where job_name = p_job_name and target_date = p_target_date
               and status = 'completed') then
    return query select 'already_completed'::text, null::uuid;
    return;
  end if;
  if exists (select 1 from public.job_runs
             where job_name = p_job_name and status = 'processing') then
    return query select 'already_processing'::text, null::uuid;
    return;
  end if;

  begin
    insert into public.job_runs (job_name, target_date, status)
      values (p_job_name, p_target_date, 'pending') returning id into v_id;
    update public.job_runs set status = 'processing', started_at = now(),
      heartbeat_at = now() where id = v_id;
  exception when unique_violation then
    -- Revierte el INSERT pending de este bloque, sin dejar filas huérfanas.
    if exists (select 1 from public.job_runs
               where job_name = p_job_name and target_date = p_target_date
                 and status = 'completed') then
      return query select 'already_completed'::text, null::uuid;
    elsif exists (select 1 from public.job_runs
                  where job_name = p_job_name and status = 'processing') then
      return query select 'already_processing'::text, null::uuid;
    else
      raise;
    end if;
    return;
  end;
  return query select 'claimed'::text, v_id;
end;
$$;

create or replace function public.heartbeat_nightly_job(p_run_id uuid)
returns boolean language plpgsql security invoker set search_path = '' as $$
begin
  update public.job_runs set heartbeat_at = now()
   where id = p_run_id and job_name = 'nightly_export' and status = 'processing';
  return found;
end;
$$;

create or replace function public.finish_nightly_job(
  p_run_id uuid, p_status text, p_error_message text default null
) returns boolean language plpgsql security invoker set search_path = '' as $$
begin
  if p_status not in ('completed', 'failed') then
    raise exception 'invalid final status';
  end if;
  update public.job_runs
     set status = p_status, finished_at = now(), heartbeat_at = now(),
         error_message = case when p_status = 'failed'
           then left(coalesce(p_error_message, 'unknown_error'), 500) else null end
   where id = p_run_id and job_name = 'nightly_export' and status = 'processing';
  return found;
end;
$$;

revoke all on function public.claim_nightly_job(text, date, integer) from public, anon, authenticated;
revoke all on function public.heartbeat_nightly_job(uuid) from public, anon, authenticated;
revoke all on function public.finish_nightly_job(uuid, text, text) from public, anon, authenticated;
grant execute on function public.claim_nightly_job(text, date, integer) to service_role;
grant execute on function public.heartbeat_nightly_job(uuid) to service_role;
grant execute on function public.finish_nightly_job(uuid, text, text) to service_role;

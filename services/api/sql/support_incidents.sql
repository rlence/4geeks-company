-- Dependencia propia de Project 7. Aplicar una vez, sin sobrescribir tablas.
create table public.support_incidents (
 id bigint generated always as identity primary key check (id <= 9007199254740991),
 title text not null check (char_length(btrim(title)) between 5 and 160),
 description text not null check (char_length(btrim(description)) between 10 and 4000),
 category text not null check (category in ('operations','technical','other')),
 status text not null default 'open' check (status in ('open','in_progress','resolved')),
 origin text not null default 'api' check (origin in ('api','backoffice')),
 created_by text not null check (created_by <> ''),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 resolved_at timestamptz,
 version integer not null default 1 check (version > 0),
 check ((status = 'resolved') = (resolved_at is not null))
);
create index support_incidents_owner_date on public.support_incidents(created_by, created_at desc, id desc);
create index support_incidents_owner_status on public.support_incidents(created_by, status, created_at desc, id desc);
create function public.support_incidents_transition() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
 if new.created_by <> old.created_by or new.id <> old.id or new.created_at <> old.created_at then
   raise exception 'Immutable incident identity' using errcode = '23514';
 end if;
 if new.status = old.status then return old; end if;
 if not ((old.status = 'open' and new.status in ('in_progress','resolved'))
      or (old.status = 'in_progress' and new.status = 'resolved')
      or (old.status = 'resolved' and new.status = 'in_progress')) then
   raise exception 'Invalid incident transition' using errcode = '23505';
 end if;
 new.version := old.version + 1;
 new.updated_at := clock_timestamp();
 new.resolved_at := case when new.status = 'resolved' then new.updated_at else null end;
 return new;
end $$;
create trigger support_incidents_transition before update on public.support_incidents
for each row execute function public.support_incidents_transition();
alter table public.support_incidents enable row level security;
revoke all on public.support_incidents from public, anon, authenticated, service_role;
grant select, insert on public.support_incidents to service_role;
grant update(status) on public.support_incidents to service_role;
revoke all on sequence public.support_incidents_id_seq from public, anon, authenticated, service_role;
grant usage on sequence public.support_incidents_id_seq to service_role;
revoke execute on function public.support_incidents_transition() from public, anon, authenticated;

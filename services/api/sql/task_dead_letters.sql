-- Proyecto 10: cola terminal auditable. Ejecutar en el SQL Editor.
create table if not exists public.task_dead_letters (
  task_id uuid primary key,
  task_name text not null check (task_name = 'reporting.weekly_report'),
  week_start date not null,
  attempt_count integer not null check (attempt_count >= 1),
  error_message text not null check (length(error_message) <= 500),
  failed_at timestamptz not null default now(),
  published_at timestamptz,
  publish_status text not null default 'pending'
    check (publish_status in ('pending', 'published'))
);

create index if not exists task_dead_letters_publish_idx
  on public.task_dead_letters (failed_at) where publish_status = 'pending';

alter table public.task_dead_letters enable row level security;
revoke all on public.task_dead_letters from anon, authenticated;
grant select, insert, update on public.task_dead_letters to service_role;

-- IM evaluation Supabase schema.
--
-- Purpose:
-- 1. Store human annotation overrides from the IM evaluation board.
-- 2. Store daily badcase statistics for the metrics dashboard.
-- 3. Keep enough sync metadata to move pending annotation rows into Hive.
--
-- Apply in Supabase SQL Editor, or with:
--   supabase db push

create table if not exists public.annotation_records (
  id bigserial primary key,

  -- Source Hive fields.
  hive_id bigint,
  session_id text not null,
  im_session_id text,
  date text not null,
  wm_poi_id text,
  user_id text,
  session_data_string text,
  intent text,
  inaccuracy_reason text,
  is_resolved integer,
  is_accurate integer,
  create_time text,
  update_time text not null,
  evaluation_workflow_version integer,
  is_resolved_label integer,
  is_accurate_label integer,
  dt text not null,

  -- Sync metadata.
  sync_status text not null default 'pending',
  sync_time timestamptz,
  sync_error text,
  annotation_time timestamptz not null default now(),

  constraint annotation_records_sync_status_check
    check (sync_status in ('pending', 'syncing', 'synced', 'failed')),
  constraint annotation_records_resolved_check
    check (is_resolved is null or is_resolved in (0, 1)),
  constraint annotation_records_accurate_check
    check (is_accurate is null or is_accurate in (0, 1, 2)),
  constraint annotation_records_resolved_label_check
    check (is_resolved_label is null or is_resolved_label in (0, 1)),
  constraint annotation_records_accurate_label_check
    check (is_accurate_label is null or is_accurate_label in (0, 1, 2)),
  constraint annotation_records_unique_session_update
    unique (session_id, update_time)
);

create index if not exists idx_annotation_records_sync_status
  on public.annotation_records (sync_status);

create index if not exists idx_annotation_records_session_id
  on public.annotation_records (session_id);

create index if not exists idx_annotation_records_im_session_id
  on public.annotation_records (im_session_id);

create index if not exists idx_annotation_records_date
  on public.annotation_records (date);

create index if not exists idx_annotation_records_dt
  on public.annotation_records (dt);

create index if not exists idx_annotation_records_annotation_time
  on public.annotation_records (annotation_time);

comment on table public.annotation_records is
  'IM evaluation annotation records. Rows are written by the evaluation board and later synced to Hive.';
comment on column public.annotation_records.hive_id is
  'Original Hive id when available. The Supabase id is only the annotation row primary key.';
comment on column public.annotation_records.session_id is
  'Evaluation session id.';
comment on column public.annotation_records.im_session_id is
  'Real IM session id.';
comment on column public.annotation_records.date is
  'Business date in yyyyMMdd format, matching IM_board Hive filters.';
comment on column public.annotation_records.dt is
  'Partition date in yyyyMMdd format.';
comment on column public.annotation_records.session_data_string is
  'Conversation JSON array. Each item contains role, content, timestamp, to_human_agent, intent, im_session_id.';
comment on column public.annotation_records.intent is
  'Formatted intent list, for example: 【商品】, 【**转人工**】.';
comment on column public.annotation_records.is_resolved is
  'Machine result: 1 means resolved, 0 means unresolved.';
comment on column public.annotation_records.is_accurate is
  'Machine score: 2 correct, 1 flawed, 0 wrong.';
comment on column public.annotation_records.is_resolved_label is
  'Human override: 1 resolved, 0 unresolved.';
comment on column public.annotation_records.is_accurate_label is
  'Human override: 2 correct, 1 flawed, 0 wrong.';
comment on column public.annotation_records.create_time is
  'Timestamp text in yyyy-MM-dd HH:mm:ss format; Spark sync casts it to Hive timestamp.';
comment on column public.annotation_records.update_time is
  'Timestamp text in yyyy-MM-dd HH:mm:ss format; unique with session_id and used for latest-row ordering.';
comment on column public.annotation_records.sync_status is
  'pending, syncing, synced, or failed.';

create table if not exists public.badcase_indicator_statistics_table (
  id bigserial primary key,
  date text not null,
  total_sessions_count integer not null default 0,
  badcase_sessions_count integer not null default 0,
  unresolved_sessions_count integer not null default 0,
  intents_count text not null default '{}',
  reasons_count text not null default '{}',
  intents text not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint badcase_indicator_statistics_date_unique unique (date),
  constraint badcase_indicator_statistics_non_negative_check
    check (
      total_sessions_count >= 0
      and badcase_sessions_count >= 0
      and unresolved_sessions_count >= 0
    )
);

create index if not exists idx_badcase_indicator_statistics_date
  on public.badcase_indicator_statistics_table (date);

comment on table public.badcase_indicator_statistics_table is
  'Daily IM auto-evaluation metrics used by the evaluation dashboard.';
comment on column public.badcase_indicator_statistics_table.date is
  'Statistics date in yyyyMMdd format.';
comment on column public.badcase_indicator_statistics_table.badcase_sessions_count is
  'Number of sessions whose effective accuracy score is 0 or 1.';
comment on column public.badcase_indicator_statistics_table.unresolved_sessions_count is
  'Number of sessions whose effective resolved value is 0.';
comment on column public.badcase_indicator_statistics_table.intents_count is
  'JSON string: inaccurate intent counts parsed from inaccuracy_reason.';
comment on column public.badcase_indicator_statistics_table.reasons_count is
  'JSON string: badcase reason counts parsed from inaccuracy_reason.';
comment on column public.badcase_indicator_statistics_table.intents is
  'JSON string: all-session intent distribution for the date.';

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_badcase_indicator_statistics_updated_at
  on public.badcase_indicator_statistics_table;

create trigger trg_badcase_indicator_statistics_updated_at
before update on public.badcase_indicator_statistics_table
for each row execute function public.set_updated_at();

create table if not exists public.im_sync_runs (
  id bigserial primary key,
  batch_id text not null unique,
  source_table text not null default 'public.annotation_records',
  target_table text not null default 'mart_waimaiunion.auto_evaluation_results',
  sync_date text,
  status text not null default 'running',
  pending_count integer not null default 0,
  synced_count integer not null default 0,
  failed_count integer not null default 0,
  error_message text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,

  constraint im_sync_runs_status_check
    check (status in ('running', 'success', 'failed', 'empty'))
);

create index if not exists idx_im_sync_runs_started_at
  on public.im_sync_runs (started_at desc);

create index if not exists idx_im_sync_runs_sync_date
  on public.im_sync_runs (sync_date);

comment on table public.im_sync_runs is
  'Minimal sync batch log for copying IM annotation rows from Supabase to Hive.';
comment on column public.im_sync_runs.batch_id is
  'Unique sync batch id generated by the sync job.';
comment on column public.im_sync_runs.status is
  'running, success, failed, or empty.';

-- The current board uses the anon Supabase client. Keep grants explicit.
grant usage on schema public to anon, authenticated;
grant select, insert, update on public.annotation_records to anon, authenticated;
grant select, insert, update on public.badcase_indicator_statistics_table to anon, authenticated;
grant select, insert, update on public.im_sync_runs to anon, authenticated;
grant usage, select on all sequences in schema public to anon, authenticated;

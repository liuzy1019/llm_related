# IM Database Schema

This directory contains the canonical database DDL for the IM auto-evaluation
and annotation flow.

## Files

- `supabase/001_im_eval_schema.sql`
  - Creates Supabase tables for annotation writes and dashboard statistics.
  - Main tables:
    - `public.annotation_records`
    - `public.badcase_indicator_statistics_table`
    - `public.im_sync_runs`

- `hive/001_auto_evaluation_results.sql`
  - Creates the Hive result table queried by the evaluation board:
    - `mart_waimaiunion.auto_evaluation_results`

- `sync/supabase_to_hive_spark.py`
  - Sanitized Spark template for copying pending Supabase annotation rows back
    to the Hive result table.

## Data Flow

1. The auto-evaluation job writes session-level results to Hive.
2. The IM board queries `mart_waimaiunion.auto_evaluation_results`.
3. Human annotation actions are written to Supabase `annotation_records`.
4. A scheduled sync job copies pending Supabase annotation rows back to Hive.
5. The board calculates daily metrics and stores them in
   `badcase_indicator_statistics_table`.

For this repo, that is the required skeleton. Raw log ingestion and full data
warehouse layering are intentionally out of scope unless the project becomes a
real production system.

## Supabase Apply

Run the SQL in the Supabase SQL Editor, or copy it into a Supabase migration and
run:

```bash
supabase db push
```

The current board uses the anon Supabase client, so the migration grants
`select`, `insert`, and `update` on the two dashboard tables to `anon` and
`authenticated`.

## Hive Apply

Run the Hive DDL in your Hive/Spark SQL environment:

```sql
source hxim-main/database/hive/001_auto_evaluation_results.sql;
```

If the table already exists, verify whether it has `im_session_id`. If not, run
the compatibility `alter table` statement at the bottom of the Hive DDL.

## Sync Template

The sync template expects credentials from environment variables:

```bash
export SUPABASE_JDBC_URL='jdbc:postgresql://host:5432/db'
export SUPABASE_DB_USER='user'
export SUPABASE_DB_PASSWORD='password'
export SYNC_DATE='20260522' # optional
```

Then run it from your Spark notebook/job environment with the PostgreSQL JDBC
driver on the Spark classpath.

The script uses `im_sync_runs` as a minimal batch log and updates
`annotation_records.sync_status` through the same PostgreSQL JDBC connection.

## Field Conventions

- `date` and `dt` both use `yyyyMMdd`.
- `session_id` is the evaluation session id.
- `im_session_id` is the real IM conversation id.
- `wm_poi_id` is the store id used by the board filters.
- `create_time` and `update_time` use `yyyy-MM-dd HH:mm:ss` timestamp text in
  Supabase and are cast to Hive `timestamp` by the sync job.
- `hive_id` in Supabase maps back to Hive `id`; runtime demo records generate a
  stable small positive bigint-compatible id from `session_id + update_time`.
- `session_data_string` is a JSON array string:

```json
[
  {
    "role": "user",
    "content": "message text",
    "timestamp": "2026-03-24 10:00:00",
    "to_human_agent": 0,
    "intent": "商品",
    "im_session_id": "xxx"
  }
]
```

- `is_resolved`: `1` means resolved, `0` means unresolved.
- `is_accurate`: `2` means correct, `1` means flawed, `0` means wrong.
- `*_label` fields are human overrides. The board should prefer label values
  when they are present.

-- IM auto-evaluation Hive table.
--
-- This table is queried by the IM evaluation board:
--   mart_waimaiunion.auto_evaluation_results
--
-- Partition:
--   dt: yyyyMMdd
--
-- Notes:
-- - session_data_string is a JSON array string. Keep it as STRING because the
--   existing board parses it on the client side.
-- - is_accurate uses 2/1/0: correct/flawed/wrong.
-- - is_resolved uses 1/0: resolved/unresolved.
-- - *_label fields are human overrides synced back from Supabase.

create database if not exists mart_waimaiunion;

create table if not exists mart_waimaiunion.auto_evaluation_results (
  id bigint comment 'Evaluation result id. Usually generated from date and sequence.',
  session_id string comment 'Evaluation session id.',
  im_session_id string comment 'Real IM session id.',
  `date` string comment 'Business date in yyyyMMdd format.',
  wm_poi_id string comment 'Waimai poi/store id.',
  user_id string comment 'User id.',
  intent string comment 'Formatted intent list, for example: 【商品】 or 【**转人工**】.',
  is_accurate int comment 'Machine score: 2 correct, 1 flawed, 0 wrong.',
  inaccuracy_reason string comment 'Badcase reason text produced by the evaluator.',
  is_resolved int comment 'Machine result: 1 resolved, 0 unresolved.',
  create_time timestamp comment 'Result creation time.',
  update_time timestamp comment 'Result update time.',
  session_data_string string comment 'Conversation JSON array string.',
  evaluation_workflow_version int comment 'Evaluation workflow version.',
  is_resolved_label int comment 'Human override: 1 resolved, 0 unresolved.',
  is_accurate_label int comment 'Human override: 2 correct, 1 flawed, 0 wrong.'
)
comment 'IM auto-evaluation result table for Huanxiong customer-service evaluation board.'
partitioned by (
  dt string comment 'Partition date in yyyyMMdd format.'
)
stored as orc
tblproperties (
  'orc.compress' = 'SNAPPY',
  'transactional' = 'false'
);

-- Optional compatibility migration for older tables created before im_session_id.
-- Run only if the table already exists and lacks the column:
-- alter table mart_waimaiunion.auto_evaluation_results
--   add columns (im_session_id string comment 'Real IM session id.');


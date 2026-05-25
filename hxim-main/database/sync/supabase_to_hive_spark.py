#!/usr/bin/env python
"""Sync pending IM annotation rows from Supabase/Postgres to Hive.

Run in a Spark environment with the PostgreSQL JDBC driver available.
Credentials are read from environment variables so they are not committed.
"""

import os
import uuid
from datetime import datetime

import pyspark.sql.functions as F


SUPABASE_JDBC_URL = os.environ["SUPABASE_JDBC_URL"]
SUPABASE_DB_USER = os.environ["SUPABASE_DB_USER"]
SUPABASE_DB_PASSWORD = os.environ["SUPABASE_DB_PASSWORD"]
SOURCE_TABLE = os.environ.get("SUPABASE_ANNOTATION_TABLE", "public.annotation_records")
TARGET_TABLE = os.environ.get("HIVE_EVALUATION_TABLE", "mart_waimaiunion.auto_evaluation_results")
SYNC_DATE = os.environ.get("SYNC_DATE")  # Optional yyyyMMdd filter.
BATCH_ID = os.environ.get("SYNC_BATCH_ID") or f"im-sync-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"


def jdbc_connection():
    props = spark._jvm.java.util.Properties()
    props.setProperty("user", SUPABASE_DB_USER)
    props.setProperty("password", SUPABASE_DB_PASSWORD)
    return spark._jvm.java.sql.DriverManager.getConnection(SUPABASE_JDBC_URL, props)


def execute_update(sql, params=None):
    params = params or []
    conn = jdbc_connection()
    try:
        stmt = conn.prepareStatement(sql)
        try:
            for idx, value in enumerate(params, start=1):
                if value is None:
                    stmt.setNull(idx, spark._jvm.java.sql.Types.VARCHAR)
                elif isinstance(value, int):
                    stmt.setInt(idx, value)
                else:
                    stmt.setString(idx, str(value))
            return stmt.executeUpdate()
        finally:
            stmt.close()
    finally:
        conn.close()


def configure_hive():
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    spark.conf.set("hive.exec.dynamic.partition.mode", "nonstrict")
    spark.conf.set("hive.exec.dynamic.partition", "true")
    spark.conf.set("hive.exec.max.dynamic.partitions", 2000)


def read_pending_annotations():
    where_parts = ["sync_status = 'pending'"]
    if SYNC_DATE:
        where_parts.append(f"dt = '{SYNC_DATE}'")
    where_sql = " AND ".join(where_parts)
    query = f"(SELECT * FROM {SOURCE_TABLE} WHERE {where_sql}) AS pending_annotations"

    return spark.read.jdbc(
        url=SUPABASE_JDBC_URL,
        table=query,
        properties={
            "user": SUPABASE_DB_USER,
            "password": SUPABASE_DB_PASSWORD,
            "driver": "org.postgresql.Driver",
        },
    )


def create_sync_run(pending_count):
    execute_update(
        """
        INSERT INTO public.im_sync_runs
          (batch_id, source_table, target_table, sync_date, status, pending_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (batch_id) DO UPDATE SET
          status = EXCLUDED.status,
          pending_count = EXCLUDED.pending_count,
          started_at = NOW(),
          finished_at = NULL,
          error_message = NULL
        """,
        [BATCH_ID, SOURCE_TABLE, TARGET_TABLE, SYNC_DATE, "running", pending_count],
    )


def finish_sync_run(status, synced_count=0, failed_count=0, error_message=None):
    execute_update(
        """
        UPDATE public.im_sync_runs
        SET status = ?,
            synced_count = ?,
            failed_count = ?,
            error_message = ?,
            finished_at = NOW()
        WHERE batch_id = ?
        """,
        [status, synced_count, failed_count, error_message, BATCH_ID],
    )


def mark_records(status, rows, error_message=None):
    if not rows:
        return 0
    conn = jdbc_connection()
    try:
        stmt = conn.prepareStatement(
            f"""
            UPDATE {SOURCE_TABLE}
            SET sync_status = ?,
                sync_time = NOW(),
                sync_error = ?
            WHERE session_id = ?
              AND update_time = ?
            """
        )
        try:
            for row in rows:
                stmt.setString(1, status)
                if error_message is None:
                    stmt.setNull(2, spark._jvm.java.sql.Types.VARCHAR)
                else:
                    stmt.setString(2, error_message[:4000])
                stmt.setString(3, str(row["session_id"]))
                stmt.setString(4, str(row["update_time"]))
                stmt.addBatch()
            result = stmt.executeBatch()
            return sum(1 for value in result if value >= 0)
        finally:
            stmt.close()
    finally:
        conn.close()


def to_hive_shape(df):
    return df.select(
        F.col("hive_id").cast("bigint").alias("id"),
        F.col("session_id").cast("string"),
        F.col("im_session_id").cast("string"),
        F.col("date").cast("string"),
        F.col("wm_poi_id").cast("string"),
        F.col("user_id").cast("string"),
        F.col("intent").cast("string"),
        F.col("is_accurate").cast("int"),
        F.col("inaccuracy_reason").cast("string"),
        F.col("is_resolved").cast("int"),
        F.to_timestamp(F.col("create_time")).alias("create_time"),
        F.to_timestamp(F.col("update_time")).alias("update_time"),
        F.col("session_data_string").cast("string"),
        F.col("evaluation_workflow_version").cast("int"),
        F.col("is_resolved_label").cast("int"),
        F.col("is_accurate_label").cast("int"),
        F.col("dt").cast("string"),
    )


def main():
    configure_hive()
    pending_df = read_pending_annotations()
    pending_count = pending_df.count()
    print(f"[{datetime.utcnow().isoformat()}Z] batch={BATCH_ID} pending rows: {pending_count}")
    create_sync_run(pending_count)

    if pending_count == 0:
        finish_sync_run("empty")
        return

    key_rows = pending_df.select("session_id", "update_time").collect()
    mark_records("syncing", key_rows)

    try:
        hive_df = to_hive_shape(pending_df)
        hive_df.write.mode("append").insertInto(TARGET_TABLE)
        synced = mark_records("synced", key_rows)
        finish_sync_run("success", synced_count=synced)
        print(f"Inserted {pending_count} rows into {TARGET_TABLE}, marked {synced} rows as synced")
    except Exception as exc:
        message = str(exc)
        failed = mark_records("failed", key_rows, message)
        finish_sync_run("failed", failed_count=failed, error_message=message[:4000])
        raise


if __name__ == "__main__":
    main()

"""Converted from talend_jobs/customer_accounts/customer_dimension_load_0.1.item.

Flow: tDBInput(Snowflake RAW.STG_CUSTOMER LEFT JOIN DIM.DIM_CUSTOMER
      for changed/new records) → tMap(SCD Type 2 fields: surrogate key,
      effective dates, IS_CURRENT) → tDBOutput(Snowflake DIM.DIM_CUSTOMER)

Source: Snowflake RAW  |  Target: Snowflake DIM.DIM_CUSTOMER
Custom routines: DateFormatUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.customer_dimension_load")


def run(session: Session, config: dict) -> None:
    src_schema = config.get("src_schema", "RAW")
    tgt_schema = config.get("tgt_schema", "DIM")
    effective_date = config.get("effective_date", "")

    # tDBInput_1: detect changed or new customers
    df = session.sql(f"""
        SELECT
            s.CUSTOMER_ID, s.FULL_NAME, s.SSN_MASKED, s.EMAIL,
            s.PHONE_PRIMARY, s.FULL_ADDRESS, s.ACCOUNT_STATUS,
            s.CREDIT_SCORE, s.CUSTOMER_SINCE, s.ETL_LOAD_TS
        FROM {src_schema}.STG_CUSTOMER s
        LEFT JOIN {tgt_schema}.DIM_CUSTOMER d
            ON s.CUSTOMER_ID = d.CUSTOMER_ID AND d.IS_CURRENT = 1
        WHERE d.CUSTOMER_ID IS NULL
           OR s.FULL_NAME != d.FULL_NAME
           OR s.EMAIL != d.EMAIL
           OR s.ACCOUNT_STATUS != d.ACCOUNT_STATUS
           OR s.CREDIT_SCORE != d.CREDIT_SCORE
    """)

    # Expire existing current records for changed customers
    session.sql(f"""
        MERGE INTO {tgt_schema}.DIM_CUSTOMER tgt
        USING (
            SELECT CUSTOMER_ID FROM {src_schema}.STG_CUSTOMER s
            WHERE EXISTS (
                SELECT 1 FROM {tgt_schema}.DIM_CUSTOMER d
                WHERE d.CUSTOMER_ID = s.CUSTOMER_ID
                  AND d.IS_CURRENT = 1
                  AND (s.FULL_NAME != d.FULL_NAME
                    OR s.EMAIL != d.EMAIL
                    OR s.ACCOUNT_STATUS != d.ACCOUNT_STATUS
                    OR s.CREDIT_SCORE != d.CREDIT_SCORE)
            )
        ) src ON tgt.CUSTOMER_ID = src.CUSTOMER_ID AND tgt.IS_CURRENT = 1
        WHEN MATCHED THEN UPDATE SET
            tgt.IS_CURRENT = 0,
            tgt.EFF_END_DATE = CURRENT_DATE()
    """).collect()

    # tMap_1: build SCD Type 2 output
    eff_date_expr = (
        F.lit(effective_date) if effective_date else F.current_date()
    )

    # Offset seq8() by the current max SK to ensure cross-run uniqueness
    max_sk_row = session.sql(
        f"SELECT COALESCE(MAX(DIM_CUSTOMER_SK), 0) AS MAX_SK FROM {tgt_schema}.DIM_CUSTOMER"
    ).collect()
    sk_offset = max_sk_row[0]["MAX_SK"] if max_sk_row else 0

    df_scd = df.select(
        (F.seq8() + F.lit(sk_offset) + F.lit(1)).alias("DIM_CUSTOMER_SK"),
        F.col("CUSTOMER_ID"),
        F.col("FULL_NAME"),
        F.col("SSN_MASKED"),
        F.col("EMAIL"),
        F.col("ACCOUNT_STATUS"),
        F.col("CREDIT_SCORE"),
        eff_date_expr.alias("EFF_START_DATE"),
        F.lit(None).cast("DATE").alias("EFF_END_DATE"),
        F.lit(1).alias("IS_CURRENT"),
    )

    # tDBOutput_1: INSERT new dimension records
    df_scd.write.mode("append").save_as_table(f"{tgt_schema}.DIM_CUSTOMER")
    logger.info("customer_dimension_load complete — SCD2 to %s.DIM_CUSTOMER", tgt_schema)


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

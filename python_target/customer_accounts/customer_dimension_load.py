"""Converted from: talend_jobs/customer_accounts/customer_dimension_load_0.1.item

SCD Type 2 dimension load for DIM_CUSTOMER. Reads changed/new customers
from RAW.STG_CUSTOMER, generates surrogate keys, sets effective dates,
and inserts new dimension records.

Components: tDBInput(Snowflake) → tMap → tDBOutput(Snowflake)
Routines:   DateFormatUtils
"""
import logging
from datetime import datetime

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    effective_date = config.get(
        "effective_date", datetime.now().strftime("%Y-%m-%d")
    )

    df = session.sql(f"""
        SELECT
            s.CUSTOMER_ID, s.FULL_NAME, s.SSN_MASKED, s.EMAIL,
            s.PHONE_PRIMARY, s.FULL_ADDRESS, s.ACCOUNT_STATUS,
            s.CREDIT_SCORE, s.CUSTOMER_SINCE, s.ETL_LOAD_TS
        FROM {config.get('src_schema', 'RAW')}.STG_CUSTOMER s
        LEFT JOIN {config.get('tgt_schema', 'DIM')}.DIM_CUSTOMER d
            ON s.CUSTOMER_ID = d.CUSTOMER_ID AND d.IS_CURRENT = 1
        WHERE d.CUSTOMER_ID IS NULL
           OR NOT EQUAL_NULL(s.FULL_NAME, d.FULL_NAME)
           OR NOT EQUAL_NULL(s.EMAIL, d.EMAIL)
           OR NOT EQUAL_NULL(s.ACCOUNT_STATUS, d.ACCOUNT_STATUS)
           OR NOT EQUAL_NULL(s.CREDIT_SCORE, d.CREDIT_SCORE)
    """)

    # Expire existing current records for changed customers
    session.sql(f"""
        UPDATE {config.get('tgt_schema', 'DIM')}.DIM_CUSTOMER
        SET IS_CURRENT = 0,
            EFF_END_DATE = '{effective_date}'
        WHERE IS_CURRENT = 1
          AND CUSTOMER_ID IN (
              SELECT s.CUSTOMER_ID
              FROM {config.get('src_schema', 'RAW')}.STG_CUSTOMER s
              JOIN {config.get('tgt_schema', 'DIM')}.DIM_CUSTOMER d
                  ON s.CUSTOMER_ID = d.CUSTOMER_ID AND d.IS_CURRENT = 1
              WHERE NOT EQUAL_NULL(s.FULL_NAME, d.FULL_NAME)
                 OR NOT EQUAL_NULL(s.EMAIL, d.EMAIL)
                 OR NOT EQUAL_NULL(s.ACCOUNT_STATUS, d.ACCOUNT_STATUS)
                 OR NOT EQUAL_NULL(s.CREDIT_SCORE, d.CREDIT_SCORE)
          )
    """).collect()

    # tMap: build SCD2 output
    df_out = df.select(
        F.monotonically_increasing_id().alias("DIM_CUSTOMER_SK"),
        F.col("CUSTOMER_ID"),
        F.col("FULL_NAME"),
        F.col("SSN_MASKED"),
        F.col("EMAIL"),
        F.col("ACCOUNT_STATUS"),
        F.col("CREDIT_SCORE"),
        F.lit(effective_date).cast("DATE").alias("EFF_START_DATE"),
        F.lit(None).cast("DATE").alias("EFF_END_DATE"),
        F.lit(1).alias("IS_CURRENT"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table(
        f"{config.get('tgt_schema', 'DIM')}.DIM_CUSTOMER"
    )
    logger.info("customer_dimension_load: inserted %d SCD2 rows", row_count)
    return row_count

"""Converted from: talend_jobs/customer_accounts/customer_extract_0.1.item

Extracts customer master records from Oracle, applies transformations
(SSN masking, address concatenation, name concatenation), and loads
to Snowflake staging table STG_CUSTOMER.

Components: tDBInput(Oracle) → tMap → tDBOutput(Snowflake)
Routines:   DateFormatUtils, AccountValidator
"""
import logging
from datetime import datetime

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    batch_date = config.get("batch_date", datetime.now().strftime("%Y-%m-%d"))

    df = session.sql(f"""
        SELECT
            c.CUSTOMER_ID, c.FIRST_NAME, c.LAST_NAME, c.SSN,
            c.DATE_OF_BIRTH, c.EMAIL, c.PHONE_PRIMARY,
            c.ADDRESS_LINE1, c.ADDRESS_LINE2, c.CITY,
            c.STATE_CODE, c.ZIP_CODE, c.ACCOUNT_STATUS,
            c.CREDIT_SCORE, c.CUSTOMER_SINCE, c.LAST_UPDATED
        FROM CUSTOMER_MASTER c
        WHERE c.LAST_UPDATED >= TO_DATE('{batch_date}', 'YYYY-MM-DD')
    """)

    # tMap transformations
    df_out = df.select(
        F.col("CUSTOMER_ID"),
        F.concat(F.col("FIRST_NAME"), F.lit(" "), F.col("LAST_NAME")).alias(
            "FULL_NAME"
        ),
        F.concat(F.lit("***-**-"), F.substring(F.col("SSN"), 8, 4)).alias(
            "SSN_MASKED"
        ),
        F.col("DATE_OF_BIRTH"),
        F.when(F.col("EMAIL").is_not_null(), F.lower(F.col("EMAIL")))
        .otherwise(F.lit(None))
        .alias("EMAIL"),
        F.col("PHONE_PRIMARY"),
        F.concat_ws(
            F.lit(", "),
            F.concat_ws(
                F.lit(" "),
                F.col("ADDRESS_LINE1"),
                F.coalesce(F.col("ADDRESS_LINE2"), F.lit("")),
            ),
            F.col("CITY"),
            F.concat_ws(F.lit(" "), F.col("STATE_CODE"), F.col("ZIP_CODE")),
        ).alias("FULL_ADDRESS"),
        F.col("ACCOUNT_STATUS"),
        F.col("CREDIT_SCORE"),
        F.col("CUSTOMER_SINCE"),
        F.current_timestamp().alias("ETL_LOAD_TS"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table(
        f"{config.get('tgt_schema', 'RAW')}.STG_CUSTOMER"
    )
    logger.info("customer_extract: loaded %d rows to STG_CUSTOMER", row_count)
    return row_count

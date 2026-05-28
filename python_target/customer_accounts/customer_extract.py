"""Converted from talend_jobs/customer_accounts/customer_extract_0.1.item.

Flow: tDBInput(Oracle CUSTOMER_MASTER) → tMap(name concat, SSN mask,
      address concat, email lowercase) → tDBOutput(Snowflake STG_CUSTOMER)

Source: Oracle 12c  |  Target: Snowflake RAW.STG_CUSTOMER
Custom routines: DateFormatUtils, AccountValidator
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import StringType

logger = logging.getLogger("etl.customer_extract")


def run(session: Session, config: dict) -> None:
    batch_date = config.get("batch_date", "")
    tgt_schema = config.get("tgt_schema", "RAW")

    # tDBInput_1: Source CUSTOMER_MASTER (Oracle → pre-staged or Snowpark SQL)
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

    # tMap_1: transformations
    df = df.with_column(
        "FULL_NAME",
        F.concat(F.col("FIRST_NAME"), F.lit(" "), F.col("LAST_NAME")),
    )
    df = df.with_column(
        "SSN_MASKED",
        F.concat(F.lit("***-**-"), F.substring(F.col("SSN"), 8, 4)),
    )
    df = df.with_column(
        "EMAIL",
        F.when(F.col("EMAIL").is_not_null(), F.lower(F.col("EMAIL"))).otherwise(
            F.lit(None).cast(StringType())
        ),
    )
    df = df.with_column(
        "FULL_ADDRESS",
        F.concat(
            F.col("ADDRESS_LINE1"),
            F.when(
                F.col("ADDRESS_LINE2").is_not_null(),
                F.concat(F.lit(" "), F.col("ADDRESS_LINE2")),
            ).otherwise(F.lit("")),
            F.lit(", "),
            F.col("CITY"),
            F.lit(", "),
            F.col("STATE_CODE"),
            F.lit(" "),
            F.col("ZIP_CODE"),
        ),
    )
    df = df.with_column("ETL_LOAD_TS", F.current_timestamp())

    # Select output columns matching tDBOutput_1 schema
    df_out = df.select(
        "CUSTOMER_ID",
        "FULL_NAME",
        "SSN_MASKED",
        "DATE_OF_BIRTH",
        "EMAIL",
        "PHONE_PRIMARY",
        "FULL_ADDRESS",
        "ACCOUNT_STATUS",
        "CREDIT_SCORE",
        "CUSTOMER_SINCE",
        "ETL_LOAD_TS",
    )

    # tDBOutput_1: INSERT to STG_CUSTOMER
    df_out.write.mode("append").save_as_table(f"{tgt_schema}.STG_CUSTOMER")
    logger.info(
        "customer_extract complete — loaded to %s.STG_CUSTOMER", tgt_schema
    )


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

"""Converted from talend_jobs/customer_accounts/customer_validation_0.1.item.

Flow: tDBInput(Oracle CUSTOMER_MASTER active) → tMap(SSN/email/phone/zip
      validation with split to valid_records + invalid_records)
      → tDBOutput(Snowflake CUSTOMER_VALIDATION_RESULTS)
      → tLogRow(invalid records)

Source: Oracle 12c  |  Target: Snowflake CUSTOMER_VALIDATION_RESULTS
Custom routines: AccountValidator
"""
import logging
import re

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import BooleanType, StringType

logger = logging.getLogger("etl.customer_validation")

SSN_NUMERIC_RE = re.compile(r"^\d{9}$")


@F.udf(return_type=BooleanType(), input_types=[StringType()])
def udf_is_valid_ssn(ssn: str) -> bool:
    if not ssn or not ssn.strip():
        return False
    cleaned = ssn.replace("-", "")
    if not SSN_NUMERIC_RE.match(cleaned):
        return False
    area, group, serial = cleaned[:3], cleaned[3:5], cleaned[5:9]
    if area in ("000", "666") or area.startswith("9"):
        return False
    if group == "00" or serial == "0000":
        return False
    return True


def run(session: Session, config: dict) -> None:
    # tDBInput_1: active customers from source
    df = session.sql("""
        SELECT CUSTOMER_ID, SSN, EMAIL, PHONE_PRIMARY,
               STATE_CODE, ZIP_CODE, ACCOUNT_STATUS
        FROM CUSTOMER_MASTER
        WHERE ACCOUNT_STATUS = 'ACTIVE'
    """)

    # tMap_1 var table: validation flags
    df = df.with_column("SSN_VALID", udf_is_valid_ssn(F.col("SSN")))
    df = df.with_column(
        "EMAIL_VALID",
        F.col("EMAIL").is_not_null() & F.col("EMAIL").contains(F.lit("@")),
    )
    df = df.with_column(
        "PHONE_VALID",
        F.col("PHONE_PRIMARY").is_not_null()
        & (F.length(F.regexp_replace(F.col("PHONE_PRIMARY"), F.lit("[^0-9]"), F.lit(""))) == F.lit(10)),
    )
    df = df.with_column(
        "ZIP_VALID",
        F.col("ZIP_CODE").is_not_null()
        & F.col("ZIP_CODE").rlike("\\d{5}(-\\d{4})?"),
    )
    df = df.with_column(
        "ALL_VALID",
        F.col("SSN_VALID") & F.col("EMAIL_VALID") & F.col("PHONE_VALID") & F.col("ZIP_VALID"),
    )

    # Valid records → CUSTOMER_VALIDATION_RESULTS
    df_valid = df.filter(F.col("ALL_VALID")).select(
        F.col("CUSTOMER_ID"),
        F.col("SSN_VALID"),
        F.col("EMAIL_VALID"),
        F.col("PHONE_VALID"),
        F.col("ZIP_VALID"),
        F.lit("PASS").alias("VALIDATION_STATUS"),
        F.current_timestamp().alias("VALIDATED_AT"),
    )
    df_valid.write.mode("append").save_as_table("CUSTOMER_VALIDATION_RESULTS")

    # Invalid records → log
    df_invalid = df.filter(~F.col("ALL_VALID")).select(
        F.col("CUSTOMER_ID"),
        F.concat(
            F.when(~F.col("SSN_VALID"), F.lit("INVALID_SSN;")).otherwise(F.lit("")),
            F.when(~F.col("EMAIL_VALID"), F.lit("INVALID_EMAIL;")).otherwise(F.lit("")),
            F.when(~F.col("PHONE_VALID"), F.lit("INVALID_PHONE;")).otherwise(F.lit("")),
            F.when(~F.col("ZIP_VALID"), F.lit("INVALID_ZIP;")).otherwise(F.lit("")),
        ).alias("VALIDATION_ERRORS"),
        F.current_timestamp().alias("FLAGGED_AT"),
    )

    invalid_count = df_invalid.count()
    if invalid_count > 0:
        logger.warning("customer_validation: %d invalid records", invalid_count)

    logger.info("customer_validation complete")


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

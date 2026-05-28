"""Converted from: talend_jobs/customer_accounts/customer_validation_0.1.item

Validates customer records (SSN, email, phone, zip) and routes to
valid_records (→ CUSTOMER_VALIDATION_RESULTS) or invalid_records (→ log).

Components: tDBInput(Oracle) → tMap(split/reject) → tDBOutput + tLogRow
Routines:   AccountValidator
"""
import logging
import re

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import BooleanType, StringType

from python_target.routines.validators import is_valid_ssn

logger = logging.getLogger("etl")


def _ssn_valid(ssn: str | None) -> bool:
    return is_valid_ssn(ssn)


def _email_valid(email: str | None) -> bool:
    return email is not None and "@" in email


def _phone_valid(phone: str | None) -> bool:
    if phone is None:
        return False
    return len(re.sub(r"[^0-9]", "", phone)) == 10


def _zip_valid(zip_code: str | None) -> bool:
    if zip_code is None:
        return False
    return bool(re.match(r"^\d{5}(-\d{4})?$", zip_code))


def run(session: Session, config: dict) -> dict:
    ssn_valid_udf = session.udf.register(
        _ssn_valid, return_type=BooleanType(), input_types=[StringType()],
        name="ssn_valid_udf", is_permanent=False, replace=True,
    )
    email_valid_udf = session.udf.register(
        _email_valid, return_type=BooleanType(), input_types=[StringType()],
        name="email_valid_udf", is_permanent=False, replace=True,
    )
    phone_valid_udf = session.udf.register(
        _phone_valid, return_type=BooleanType(), input_types=[StringType()],
        name="phone_valid_udf", is_permanent=False, replace=True,
    )
    zip_valid_udf = session.udf.register(
        _zip_valid, return_type=BooleanType(), input_types=[StringType()],
        name="zip_valid_udf", is_permanent=False, replace=True,
    )

    df = session.sql("""
        SELECT CUSTOMER_ID, SSN, EMAIL, PHONE_PRIMARY,
               STATE_CODE, ZIP_CODE, ACCOUNT_STATUS
        FROM CUSTOMER_MASTER
        WHERE ACCOUNT_STATUS = 'ACTIVE'
    """)

    df = df.with_columns(
        ["SSN_VALID", "EMAIL_VALID", "PHONE_VALID", "ZIP_VALID"],
        [
            ssn_valid_udf(F.col("SSN")),
            email_valid_udf(F.col("EMAIL")),
            phone_valid_udf(F.col("PHONE_PRIMARY")),
            zip_valid_udf(F.col("ZIP_CODE")),
        ],
    )
    df = df.with_column(
        "ALL_VALID",
        F.col("SSN_VALID") & F.col("EMAIL_VALID")
        & F.col("PHONE_VALID") & F.col("ZIP_VALID"),
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
    valid_count = df_valid.count()
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
    logger.info(
        "customer_validation: %d valid, %d invalid", valid_count, invalid_count
    )

    return {"valid": valid_count, "invalid": invalid_count}

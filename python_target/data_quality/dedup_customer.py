"""Converted from talend_jobs/data_quality/dedup_customer_0.1.item.

Flow: tDBInput(Snowflake STG_CUSTOMER self-join for potential duplicates)
      → tMap(SSN/email/name match scoring, confidence, match type)
      → tDBOutput(Snowflake CUSTOMER_DEDUP_RESULTS) + tLogRow(dedup log)

Source: Snowflake STG_CUSTOMER  |  Target: Snowflake CUSTOMER_DEDUP_RESULTS
Custom routines: AccountValidator (for SSN validation)
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.dedup_customer")


def run(session: Session, config: dict) -> None:
    similarity_threshold = float(config.get("similarity_threshold", 0.85))

    # tDBInput_1: self-join for potential duplicate pairs
    jaro_pct = int(similarity_threshold * 100)
    df = session.sql(f"""
        SELECT
            c1.CUSTOMER_ID AS CUSTOMER_ID_1,
            c2.CUSTOMER_ID AS CUSTOMER_ID_2,
            c1.FULL_NAME AS NAME_1, c2.FULL_NAME AS NAME_2,
            c1.SSN_MASKED AS SSN_1, c2.SSN_MASKED AS SSN_2,
            c1.EMAIL AS EMAIL_1, c2.EMAIL AS EMAIL_2
        FROM STG_CUSTOMER c1
        JOIN STG_CUSTOMER c2
            ON c1.CUSTOMER_ID < c2.CUSTOMER_ID
            AND (c1.SSN_MASKED = c2.SSN_MASKED
                 OR c1.EMAIL = c2.EMAIL
                 OR JAROWINKLER_SIMILARITY(c1.FULL_NAME, c2.FULL_NAME) > {jaro_pct})
    """)

    # tMap_1 var table: match classification
    df = df.with_column(
        "SSN_MATCH",
        F.col("SSN_1").is_not_null()
        & F.col("SSN_2").is_not_null()
        & (F.col("SSN_1") == F.col("SSN_2")),
    )
    df = df.with_column(
        "EMAIL_MATCH",
        F.col("EMAIL_1").is_not_null()
        & F.col("EMAIL_2").is_not_null()
        & (F.upper(F.col("EMAIL_1")) == F.upper(F.col("EMAIL_2"))),
    )
    df = df.with_column(
        "NAME_MATCH",
        F.upper(F.col("NAME_1")) == F.upper(F.col("NAME_2")),
    )
    df = df.with_column(
        "MATCH_TYPE",
        F.when(F.col("SSN_MATCH"), F.lit("SSN"))
        .when(F.col("EMAIL_MATCH"), F.lit("EMAIL"))
        .otherwise(F.lit("NAME")),
    )
    df = df.with_column(
        "CONFIDENCE",
        F.when(F.col("SSN_MATCH"), F.lit(0.99))
        .when(F.col("EMAIL_MATCH"), F.lit(0.95))
        .otherwise(F.lit(0.85)),
    )

    # Output 1: dedup_results → CUSTOMER_DEDUP_RESULTS
    df_results = df.select(
        F.col("CUSTOMER_ID_1").alias("MASTER_ID"),
        F.col("CUSTOMER_ID_2").alias("DUPLICATE_ID"),
        "MATCH_TYPE",
        "CONFIDENCE",
        F.current_timestamp().alias("DETECTED_AT"),
    )
    df_results.write.mode("append").save_as_table("CUSTOMER_DEDUP_RESULTS")

    # Output 2: dedup_log → tLogRow
    df_log = df.select(
        "CUSTOMER_ID_1", "CUSTOMER_ID_2",
        F.concat(
            F.lit("SSN="), F.col("SSN_MATCH").cast("STRING"),
            F.lit(";EMAIL="), F.col("EMAIL_MATCH").cast("STRING"),
            F.lit(";NAME="), F.col("NAME_MATCH").cast("STRING"),
            F.lit(";conf="), F.col("CONFIDENCE").cast("STRING"),
        ).alias("MATCH_DETAILS"),
    )
    log_count = df_log.count()
    logger.info("dedup_customer complete — %d duplicate pairs found", log_count)


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

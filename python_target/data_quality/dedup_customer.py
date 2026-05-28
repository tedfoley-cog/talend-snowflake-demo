"""Converted from: talend_jobs/data_quality/dedup_customer_0.1.item

Identifies potential duplicate customers using SSN matching, email
matching, and Jaro-Winkler name similarity. Classifies match type
and confidence, writes to CUSTOMER_DEDUP_RESULTS and logs details.

Components: tDBInput(Snowflake) → tMap(split) → tDBOutput + tLogRow
Routines:   AccountValidator
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> dict:
    similarity_threshold = config.get("similarity_threshold", 0.85)
    jw_int_threshold = int(similarity_threshold * 100)

    df = session.sql(f"""
        SELECT
            c1.CUSTOMER_ID AS CUSTOMER_ID_1,
            c2.CUSTOMER_ID AS CUSTOMER_ID_2,
            c1.FULL_NAME AS NAME_1,
            c2.FULL_NAME AS NAME_2,
            c1.SSN_MASKED AS SSN_1,
            c2.SSN_MASKED AS SSN_2,
            c1.EMAIL AS EMAIL_1,
            c2.EMAIL AS EMAIL_2
        FROM STG_CUSTOMER c1
        JOIN STG_CUSTOMER c2
            ON c1.CUSTOMER_ID < c2.CUSTOMER_ID
            AND (c1.SSN_MASKED = c2.SSN_MASKED
                 OR c1.EMAIL = c2.EMAIL
                 OR JAROWINKLER_SIMILARITY(c1.FULL_NAME, c2.FULL_NAME) > {jw_int_threshold})
    """)

    # tMap: classify match type and confidence
    df_results = df.select(
        F.col("CUSTOMER_ID_1").alias("MASTER_ID"),
        F.col("CUSTOMER_ID_2").alias("DUPLICATE_ID"),
        F.when(
            F.col("SSN_1") == F.col("SSN_2"), F.lit("SSN_MATCH")
        )
        .when(
            F.col("EMAIL_1") == F.col("EMAIL_2"), F.lit("EMAIL_MATCH")
        )
        .otherwise(F.lit("NAME_SIMILARITY"))
        .alias("MATCH_TYPE"),
        F.when(F.col("SSN_1") == F.col("SSN_2"), F.lit(0.99))
        .when(F.col("EMAIL_1") == F.col("EMAIL_2"), F.lit(0.95))
        .otherwise(
            F.lit(similarity_threshold)
        )
        .alias("CONFIDENCE"),
        F.current_timestamp().alias("DETECTED_AT"),
    )

    result_count = df_results.count()
    df_results.write.mode("append").save_as_table("CUSTOMER_DEDUP_RESULTS")

    # Log match details
    df_log = df.select(
        F.col("CUSTOMER_ID_1"),
        F.col("CUSTOMER_ID_2"),
        F.concat(
            F.lit("name1="), F.col("NAME_1"),
            F.lit(";name2="), F.col("NAME_2"),
            F.lit(";ssn_match="),
            F.when(F.col("SSN_1") == F.col("SSN_2"), F.lit("Y")).otherwise(F.lit("N")),
            F.lit(";email_match="),
            F.when(F.col("EMAIL_1") == F.col("EMAIL_2"), F.lit("Y")).otherwise(
                F.lit("N")
            ),
        ).alias("MATCH_DETAILS"),
    )
    log_count = df_log.count()
    logger.info(
        "dedup_customer: found %d potential duplicates, %d log entries",
        result_count,
        log_count,
    )

    return {"duplicates": result_count, "log_entries": log_count}

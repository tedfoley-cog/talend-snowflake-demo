"""Converted from: talend_jobs/payment_reconciliation/payment_settlement_0.1.item

Processes matched unsettled payments: classifies as AUTO or
MANUAL_REVIEW based on threshold, writes to PAYMENT_SETTLEMENT,
and marks source payments as reconciled via MERGE.

Components: tDBInput(Snowflake) → tMap → tDBOutput + tDBRow(Oracle)
Routines:   AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    threshold = config.get("auto_settle_threshold", 5000.00)

    df = session.sql("""
        SELECT pr.PAYMENT_ID, pr.LOAN_ID, pr.CUSTOMER_ID,
               pr.PAYMENT_AMOUNT, pr.AMOUNT_DUE, pr.VARIANCE, pr.MATCH_STATUS
        FROM PAYMENT_RECONCILIATION pr
        WHERE pr.MATCH_STATUS = 'MATCHED'
          AND pr.SETTLEMENT_STATUS IS NULL
    """)

    # tMap transformations
    df_out = df.select(
        F.col("PAYMENT_ID"),
        F.col("LOAN_ID"),
        F.round(F.col("PAYMENT_AMOUNT"), 2).alias("SETTLEMENT_AMOUNT"),
        F.when(
            F.col("PAYMENT_AMOUNT") <= F.lit(threshold), F.lit("AUTO")
        )
        .otherwise(F.lit("MANUAL_REVIEW"))
        .alias("SETTLEMENT_TYPE"),
        F.current_timestamp().alias("SETTLED_AT"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table("PAYMENT_SETTLEMENT")

    # Mark settled in PAYMENT_RECONCILIATION to prevent re-processing
    session.sql("""
        UPDATE PAYMENT_RECONCILIATION
        SET SETTLEMENT_STATUS = 'SETTLED'
        WHERE MATCH_STATUS = 'MATCHED' AND SETTLEMENT_STATUS IS NULL
    """).collect()

    # Mark reconciled in source (replaces tDBRow per-row UPDATE)
    session.sql("""
        MERGE INTO INCOMING_PAYMENTS tgt
        USING (
            SELECT PAYMENT_ID
            FROM PAYMENT_RECONCILIATION
            WHERE MATCH_STATUS = 'MATCHED' AND SETTLEMENT_STATUS = 'SETTLED'
        ) src
        ON tgt.PAYMENT_ID = src.PAYMENT_ID
        WHEN MATCHED THEN UPDATE SET
            tgt.RECONCILED = 'Y',
            tgt.RECONCILED_DATE = CURRENT_TIMESTAMP()
    """).collect()

    logger.info("payment_settlement: settled %d payments", row_count)
    return row_count

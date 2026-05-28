"""Converted from talend_jobs/payment_reconciliation/payment_settlement_0.1.item.

Flow: tDBInput(Snowflake PAYMENT_RECONCILIATION matched unsettled)
      → tMap(settlement amount, auto/manual classification)
      → tDBOutput(Snowflake PAYMENT_SETTLEMENT)
      + tDBRow(Oracle UPDATE INCOMING_PAYMENTS mark reconciled)

Source: Snowflake  |  Target: Snowflake PAYMENT_SETTLEMENT + Oracle writeback
Custom routines: AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.payment_settlement")


def run(session: Session, config: dict) -> None:
    auto_settle_threshold = float(config.get("auto_settle_threshold", 5000.00))

    # tDBInput_1: matched payments awaiting settlement
    df = session.sql("""
        SELECT pr.PAYMENT_ID, pr.LOAN_ID, pr.CUSTOMER_ID,
               pr.PAYMENT_AMOUNT, pr.AMOUNT_DUE, pr.VARIANCE, pr.MATCH_STATUS
        FROM PAYMENT_RECONCILIATION pr
        WHERE pr.MATCH_STATUS = 'MATCHED'
          AND pr.SETTLEMENT_STATUS IS NULL
    """)

    # tMap_1: settlement classification
    df = df.with_column(
        "SETTLEMENT_AMOUNT", F.round(F.col("PAYMENT_AMOUNT"), 2)
    )
    df = df.with_column(
        "SETTLEMENT_TYPE",
        F.when(
            F.col("PAYMENT_AMOUNT") <= F.lit(auto_settle_threshold),
            F.lit("AUTO"),
        ).otherwise(F.lit("MANUAL_REVIEW")),
    )
    df = df.with_column("SETTLED_AT", F.current_timestamp())

    df_out = df.select(
        "PAYMENT_ID", "LOAN_ID", "SETTLEMENT_AMOUNT",
        "SETTLEMENT_TYPE", "SETTLED_AT",
    )

    # Stage current batch to temp table for scoped MERGE
    df_out.write.mode("overwrite").save_as_table("__PAYMENT_SETTLEMENT_STG")

    # tDBOutput_1: INSERT settlement records from staging
    session.sql("""
        INSERT INTO PAYMENT_SETTLEMENT
        SELECT * FROM __PAYMENT_SETTLEMENT_STG
    """).collect()

    # tDBRow_1: mark only current batch as reconciled (scoped MERGE)
    session.sql("""
        MERGE INTO INCOMING_PAYMENTS tgt
        USING __PAYMENT_SETTLEMENT_STG src ON tgt.PAYMENT_ID = src.PAYMENT_ID
        WHEN MATCHED THEN UPDATE SET
            tgt.RECONCILED = 'Y',
            tgt.RECONCILED_DATE = CURRENT_TIMESTAMP()
    """).collect()

    logger.info("payment_settlement complete")


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

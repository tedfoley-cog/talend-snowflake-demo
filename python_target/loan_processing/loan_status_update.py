"""Converted from: talend_jobs/loan_processing/loan_status_update_0.1.item

Reads recent risk scores from Snowflake and updates the source
LOAN_APPLICATION table in Oracle via batch MERGE (replaces tDBRow
row-by-row dynamic SQL).

Components: tDBInput(Snowflake) → tDBRow(Oracle) → tLogRow
Routines:   (none custom)
"""
import logging

from snowflake.snowpark import Session

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    df = session.sql("""
        SELECT APPLICATION_ID, CUSTOMER_ID, DECISION, RISK_SCORE, SCORED_AT
        FROM LOAN_RISK_SCORES
        WHERE SCORED_AT >= DATEADD(day, -1, CURRENT_DATE())
    """)

    # Batch MERGE replaces per-row tDBRow UPDATE
    session.sql("""
        MERGE INTO LOAN_APPLICATION tgt
        USING (
            SELECT APPLICATION_ID, DECISION, RISK_SCORE
            FROM LOAN_RISK_SCORES
            WHERE SCORED_AT >= DATEADD(day, -1, CURRENT_DATE())
        ) src
        ON tgt.APPLICATION_ID = src.APPLICATION_ID
        WHEN MATCHED THEN UPDATE SET
            tgt.STATUS = src.DECISION,
            tgt.RISK_SCORE = src.RISK_SCORE,
            tgt.LAST_UPDATED = CURRENT_TIMESTAMP()
    """).collect()

    row_count = df.count()
    logger.info("loan_status_update: updated %d applications", row_count)
    return row_count

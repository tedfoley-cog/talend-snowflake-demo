"""Converted from talend_jobs/loan_processing/loan_status_update_0.1.item.

Flow: tDBInput(Snowflake LOAN_RISK_SCORES recent) → tDBRow(UPDATE
      Oracle LOAN_APPLICATION per row) → tLogRow

Source: Snowflake  |  Target: Oracle LOAN_APPLICATION (batch MERGE)
"""
import logging

from snowflake.snowpark import Session

logger = logging.getLogger("etl.loan_status_update")


def run(session: Session, config: dict) -> None:
    # tDBInput_1: recent risk scores from Snowflake
    df = session.sql("""
        SELECT APPLICATION_ID, CUSTOMER_ID, DECISION, RISK_SCORE, SCORED_AT
        FROM LOAN_RISK_SCORES
        WHERE SCORED_AT >= DATEADD(day, -1, CURRENT_DATE())
    """)

    # tDBRow_1: batch update replaces row-by-row dynamic SQL
    # In original Talend job this was per-row UPDATE with string concatenation;
    # converted to a MERGE for safety and performance.
    session.sql("""
        MERGE INTO LOAN_APPLICATION tgt
        USING LOAN_RISK_SCORES src
            ON tgt.APPLICATION_ID = src.APPLICATION_ID
            AND src.SCORED_AT >= DATEADD(day, -1, CURRENT_DATE())
        WHEN MATCHED THEN UPDATE SET
            tgt.STATUS = src.DECISION,
            tgt.RISK_SCORE = src.RISK_SCORE,
            tgt.LAST_UPDATED = CURRENT_TIMESTAMP()
    """).collect()

    # tLogRow_1: log summary
    count = df.count()
    logger.info("loan_status_update complete — %d applications updated", count)


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

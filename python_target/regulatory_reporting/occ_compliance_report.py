"""Converted from talend_jobs/regulatory_reporting/occ_compliance_report_0.1.item.

Flow: tDBInput(Snowflake LOAN_PORTFOLIO_VIEW aggregated)
      → tMap(compute decline rate, delinquency rates 30/60/90)
      → tDBOutput(Snowflake OCC_COMPLIANCE_REPORT INSERT)

Source: Snowflake  |  Target: Snowflake OCC_COMPLIANCE_REPORT
Custom routines: AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.occ_compliance_report")


def run(session: Session, config: dict) -> None:
    quarter = config.get("quarter", "Q1-2024")

    # tDBInput_1: portfolio summary aggregation
    df = session.sql("""
        SELECT
            LOAN_TYPE,
            COUNT(*) AS TOTAL_LOANS,
            SUM(REQUESTED_AMOUNT) AS TOTAL_VOLUME,
            AVG(RISK_SCORE) AS AVG_RISK,
            COUNT(CASE WHEN DECISION = 'AUTO_DECLINE' THEN 1 END) AS DECLINE_COUNT,
            COUNT(CASE WHEN DAYS_PAST_DUE > 30 THEN 1 END) AS DELINQUENT_30,
            COUNT(CASE WHEN DAYS_PAST_DUE > 60 THEN 1 END) AS DELINQUENT_60,
            COUNT(CASE WHEN DAYS_PAST_DUE > 90 THEN 1 END) AS DELINQUENT_90
        FROM LOAN_PORTFOLIO_VIEW
        GROUP BY LOAN_TYPE
    """)

    # tMap_1: rate calculations
    df = df.with_column(
        "DECLINE_RATE",
        F.when(
            F.col("TOTAL_LOANS") > 0,
            F.round(F.col("DECLINE_COUNT") / F.col("TOTAL_LOANS"), 4),
        ).otherwise(F.lit(0)),
    )
    df = df.with_column(
        "DELINQUENCY_RATE_30",
        F.when(
            F.col("TOTAL_LOANS") > 0,
            F.round(F.col("DELINQUENT_30") / F.col("TOTAL_LOANS"), 4),
        ).otherwise(F.lit(0)),
    )
    df = df.with_column(
        "DELINQUENCY_RATE_60",
        F.when(
            F.col("TOTAL_LOANS") > 0,
            F.round(F.col("DELINQUENT_60") / F.col("TOTAL_LOANS"), 4),
        ).otherwise(F.lit(0)),
    )
    df = df.with_column(
        "DELINQUENCY_RATE_90",
        F.when(
            F.col("TOTAL_LOANS") > 0,
            F.round(F.col("DELINQUENT_90") / F.col("TOTAL_LOANS"), 4),
        ).otherwise(F.lit(0)),
    )
    df = df.with_column("QUARTER", F.lit(quarter))

    df_out = df.select(
        "LOAN_TYPE", "TOTAL_LOANS", "TOTAL_VOLUME",
        "DECLINE_RATE", "DELINQUENCY_RATE_30",
        "DELINQUENCY_RATE_60", "DELINQUENCY_RATE_90", "QUARTER",
    )

    # tDBOutput_1: INSERT to OCC_COMPLIANCE_REPORT
    df_out.write.mode("append").save_as_table("OCC_COMPLIANCE_REPORT")
    logger.info("occ_compliance_report complete for %s", quarter)


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

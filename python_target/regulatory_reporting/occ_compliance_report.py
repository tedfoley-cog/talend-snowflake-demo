"""Converted from: talend_jobs/regulatory_reporting/occ_compliance_report_0.1.item

OCC quarterly compliance report: calculates decline rates and
delinquency rates per loan type from aggregated portfolio view.

Components: tDBInput(Snowflake) → tMap → tDBOutput(Snowflake)
Routines:   AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    quarter = config.get("quarter", "Q1-2024")

    df = session.sql("""
        SELECT LOAN_TYPE,
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

    # tMap: compute rates
    df_out = df.select(
        F.col("LOAN_TYPE"),
        F.col("TOTAL_LOANS"),
        F.col("TOTAL_VOLUME"),
        F.round(F.col("DECLINE_COUNT") / F.col("TOTAL_LOANS"), 4).alias(
            "DECLINE_RATE"
        ),
        F.round(F.col("DELINQUENT_30") / F.col("TOTAL_LOANS"), 4).alias(
            "DELINQUENCY_RATE_30"
        ),
        F.round(F.col("DELINQUENT_60") / F.col("TOTAL_LOANS"), 4).alias(
            "DELINQUENCY_RATE_60"
        ),
        F.round(F.col("DELINQUENT_90") / F.col("TOTAL_LOANS"), 4).alias(
            "DELINQUENCY_RATE_90"
        ),
        F.lit(quarter).alias("QUARTER"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table("OCC_COMPLIANCE_REPORT")
    logger.info("occ_compliance_report: generated %d rows for %s", row_count, quarter)
    return row_count

"""Converted from: talend_jobs/regulatory_reporting/cfpb_extract_0.1.item

CFPB regulatory extract: joins loan applications with customer
demographics, enriches with fiscal quarter and formatted amounts,
outputs to Snowflake table and pipe-delimited archive file.

Components: tDBInput(Oracle)[x2] → tMap(join) → tDBOutput(Snowflake) + tFileOutputDelimited
Routines:   AmountUtils, DateFormatUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    period_start = config.get("reporting_period_start", "2024-01-01")
    period_end = config.get("reporting_period_end", "2024-03-31")
    output_dir = config.get("output_dir", "/data/regulatory/cfpb/")

    # Two source inputs joined via tMap on CUSTOMER_ID
    df_loans = session.sql(f"""
        SELECT la.APPLICATION_ID, la.CUSTOMER_ID, la.LOAN_TYPE,
               la.REQUESTED_AMOUNT, la.APPLICATION_DATE, la.STATUS,
               lr.DECISION, lr.RISK_SCORE
        FROM LOAN_APPLICATION la
        LEFT JOIN LOAN_RISK_SCORES lr
            ON la.APPLICATION_ID = lr.APPLICATION_ID
        WHERE la.APPLICATION_DATE
            BETWEEN TO_DATE('{period_start}', 'YYYY-MM-DD')
                AND TO_DATE('{period_end}', 'YYYY-MM-DD')
    """)

    df_customers = session.sql("""
        SELECT CUSTOMER_ID, STATE_CODE, ZIP_CODE, CREDIT_SCORE,
               ANNUAL_INCOME, DATE_OF_BIRTH
        FROM CUSTOMER_MASTER
    """)

    df_joined = df_loans.join(df_customers, on="CUSTOMER_ID", how="left")

    # tMap expressions → Snowpark
    df_out = df_joined.select(
        F.col("APPLICATION_ID"),
        F.col("CUSTOMER_ID"),
        F.col("LOAN_TYPE"),
        F.col("REQUESTED_AMOUNT"),
        F.col("APPLICATION_DATE"),
        F.col("STATUS"),
        F.coalesce(F.col("DECISION"), F.lit("PENDING")).alias("DECISION"),
        F.col("RISK_SCORE"),
        F.col("STATE_CODE"),
        F.col("ZIP_CODE"),
        df_customers["CREDIT_SCORE"].alias("CUST_CREDIT_SCORE"),
        F.col("ANNUAL_INCOME"),
        F.to_varchar(F.col("APPLICATION_DATE"), "YYYY-\"Q\"Q").alias(
            "FISCAL_QUARTER"
        ),
        F.concat(F.lit("$"), F.to_varchar(F.col("REQUESTED_AMOUNT"), "999,999,999.99"))
        .alias("FORMATTED_AMOUNT"),
        F.current_timestamp().alias("EXTRACTED_AT"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table("CFPB_REPORTING_EXTRACT")

    # Archive file (pipe-delimited)
    rows = df_out.collect()
    if rows:
        import pandas as pd

        df_pd = pd.DataFrame([r.as_dict() for r in rows])
        archive_path = f"{output_dir}cfpb_extract_{period_start}_{period_end}.csv"
        df_pd.to_csv(archive_path, sep="|", index=False, encoding="utf-8")
        logger.info("cfpb_extract: archived to %s", archive_path)

    logger.info("cfpb_extract: extracted %d rows", row_count)
    return row_count

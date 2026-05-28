"""Converted from: talend_jobs/regulatory_reporting/cfpb_extract_0.1.item

CFPB HMDA regulatory extract: joins loan applications with customer
demographics and adverse actions, derives ACTION_TAKEN, INCOME_BRACKET,
CENSUS_TRACT, and outputs to pipe-delimited archive file.

Components: tDBInput(Oracle)[x3] → tMap(join) → tFileOutputDelimited
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

    # row1: Loan applications with risk scores
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

    # row2: Customer demographics
    df_customers = session.sql("""
        SELECT CUSTOMER_ID, STATE_CODE, ZIP_CODE, CREDIT_SCORE,
               ANNUAL_INCOME, DATE_OF_BIRTH
        FROM CUSTOMER_MASTER
    """)

    # row3: Adverse actions
    df_adverse = session.sql(f"""
        SELECT APPLICATION_ID, ADVERSE_ACTION_CODE, ADVERSE_ACTION_DATE,
               NOTICE_SENT
        FROM ADVERSE_ACTIONS
        WHERE ADVERSE_ACTION_DATE
            BETWEEN TO_DATE('{period_start}', 'YYYY-MM-DD')
                AND TO_DATE('{period_end}', 'YYYY-MM-DD')
    """)

    # tMap joins: row1 LEFT JOIN row2 ON CUSTOMER_ID, LEFT JOIN row3 ON APPLICATION_ID
    df_joined = df_loans.join(df_customers, on="CUSTOMER_ID", how="left")
    df_joined = df_joined.join(df_adverse, on="APPLICATION_ID", how="left")

    # tMap expressions: ACTION_TAKEN, INCOME_BRACKET, CENSUS_TRACT, REPORT_PERIOD
    df_out = df_joined.select(
        F.col("APPLICATION_ID"),
        F.col("LOAN_TYPE"),
        F.concat(
            F.lit("$"),
            F.to_varchar(F.col("REQUESTED_AMOUNT"), "999,999,999.99"),
        ).alias("REQUESTED_AMOUNT"),
        F.to_varchar(F.col("APPLICATION_DATE"), "MM/DD/YYYY").alias(
            "APPLICATION_DATE"
        ),
        # Var.actionTaken: adverse action → DENIED, else DECISION, else STATUS
        F.when(
            F.col("ADVERSE_ACTION_CODE").is_not_null(), F.lit("DENIED")
        )
        .when(F.col("DECISION").is_not_null(), F.col("DECISION"))
        .otherwise(F.col("STATUS"))
        .alias("ACTION_TAKEN"),
        F.col("STATE_CODE"),
        # CENSUS_TRACT = first 3 chars of ZIP_CODE
        F.when(
            F.col("ZIP_CODE").is_not_null(),
            F.substring(F.col("ZIP_CODE"), 1, 3),
        )
        .otherwise(F.lit(None))
        .alias("CENSUS_TRACT"),
        # Var.incomeBracket: <50k LOW, <100k MEDIUM, else HIGH
        F.when(F.col("ANNUAL_INCOME").is_null(), F.lit("NOT_REPORTED"))
        .when(F.col("ANNUAL_INCOME") < F.lit(50000), F.lit("LOW"))
        .when(F.col("ANNUAL_INCOME") < F.lit(100000), F.lit("MEDIUM"))
        .otherwise(F.lit("HIGH"))
        .alias("INCOME_BRACKET"),
        F.lit(f"{period_start} to {period_end}").alias("REPORT_PERIOD"),
    )

    row_count = df_out.count()

    # Archive file (pipe-delimited CFPB HMDA format)
    rows = df_out.collect()
    if rows:
        import pandas as pd

        df_pd = pd.DataFrame([r.as_dict() for r in rows])
        archive_path = f"{output_dir}cfpb_hmda_{period_end}.csv"
        df_pd.to_csv(archive_path, sep="|", index=False, encoding="utf-8")
        logger.info("cfpb_extract: archived to %s", archive_path)

    logger.info("cfpb_extract: extracted %d rows", row_count)
    return row_count

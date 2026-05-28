"""Converted from talend_jobs/regulatory_reporting/cfpb_extract_0.1.item.

Flow: tDBInput_1(Oracle LOAN_APPLICATION + LOAN_RISK_SCORES)
      + tDBInput_2(Oracle CUSTOMER_MASTER demographics)
      + tDBInput_3(Oracle ADVERSE_ACTIONS)
      → tMap(3-way LEFT JOIN, action taken logic, income bracket,
             date format, currency format, census tract)
      → tFileOutputDelimited(pipe-delimited CFPB HMDA file)

Source: Oracle 12c (3 inputs)  |  Target: CSV file
Custom routines: AmountUtils, DateFormatUtils
"""
import logging

import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

from python_target.routines.amount_utils import format_currency

logger = logging.getLogger("etl.cfpb_extract")


def run(session: Session, config: dict) -> None:
    period_start = config.get("reporting_period_start", "2024-01-01")
    period_end = config.get("reporting_period_end", "2024-03-31")
    output_dir = config.get("output_dir", "/data/regulatory/cfpb/")

    # tDBInput_1: loan applications with risk scores
    df_apps = session.sql(f"""
        SELECT la.APPLICATION_ID, la.CUSTOMER_ID, la.LOAN_TYPE,
               la.REQUESTED_AMOUNT, la.APPLICATION_DATE, la.STATUS,
               lr.DECISION, lr.RISK_SCORE
        FROM LOAN_APPLICATION la
        LEFT JOIN LOAN_RISK_SCORES lr ON la.APPLICATION_ID = lr.APPLICATION_ID
        WHERE la.APPLICATION_DATE BETWEEN
            TO_DATE('{period_start}', 'YYYY-MM-DD') AND
            TO_DATE('{period_end}', 'YYYY-MM-DD')
    """)

    # tDBInput_2: customer demographics
    df_demo = session.sql("""
        SELECT CUSTOMER_ID, STATE_CODE, ZIP_CODE, CREDIT_SCORE,
               ANNUAL_INCOME, DATE_OF_BIRTH
        FROM CUSTOMER_MASTER
    """)

    # tDBInput_3: adverse actions
    df_adverse = session.sql(f"""
        SELECT APPLICATION_ID, ADVERSE_ACTION_CODE, ADVERSE_ACTION_DATE,
               NOTICE_SENT
        FROM ADVERSE_ACTIONS
        WHERE ADVERSE_ACTION_DATE BETWEEN
            TO_DATE('{period_start}', 'YYYY-MM-DD') AND
            TO_DATE('{period_end}', 'YYYY-MM-DD')
    """)

    # tMap_1: 3-way LEFT JOIN
    df = df_apps.join(df_demo, on="CUSTOMER_ID", how="left")
    df = df.join(df_adverse, on="APPLICATION_ID", how="left")

    # Action taken: DENIED if adverse action exists, else DECISION or STATUS
    df = df.with_column(
        "ACTION_TAKEN",
        F.when(F.col("ADVERSE_ACTION_CODE").is_not_null(), F.lit("DENIED"))
        .when(F.col("DECISION").is_not_null(), F.col("DECISION"))
        .otherwise(F.col("STATUS")),
    )

    # Income bracket
    df = df.with_column(
        "INCOME_BRACKET",
        F.when(F.col("ANNUAL_INCOME").is_null(), F.lit("NOT_REPORTED"))
        .when(F.col("ANNUAL_INCOME") < 50000, F.lit("LOW"))
        .when(F.col("ANNUAL_INCOME") < 100000, F.lit("MEDIUM"))
        .otherwise(F.lit("HIGH")),
    )

    # Census tract from ZIP prefix
    df = df.with_column(
        "CENSUS_TRACT",
        F.when(
            F.col("ZIP_CODE").is_not_null(),
            F.substring(F.col("ZIP_CODE"), 1, 3),
        ),
    )

    # Date formatting + currency
    df = df.with_column(
        "APPLICATION_DATE_FMT",
        F.to_char(F.col("APPLICATION_DATE"), "MM/DD/YYYY"),
    )
    df = df.with_column(
        "REPORT_PERIOD", F.lit(f"{period_start} to {period_end}")
    )

    # Collect to pandas for file output (tFileOutputDelimited)
    pdf = df.select(
        "APPLICATION_ID", "LOAN_TYPE", "REQUESTED_AMOUNT",
        "APPLICATION_DATE_FMT", "ACTION_TAKEN", "STATE_CODE",
        "CENSUS_TRACT", "INCOME_BRACKET", "REPORT_PERIOD",
    ).to_pandas()

    pdf = pdf.rename(columns={"APPLICATION_DATE_FMT": "APPLICATION_DATE"})
    pdf["REQUESTED_AMOUNT"] = pdf["REQUESTED_AMOUNT"].apply(
        lambda x: format_currency(float(x)) if pd.notna(x) else ""
    )

    out_path = f"{output_dir}cfpb_hmda_{period_end}.csv"
    pdf.to_csv(out_path, sep="|", index=False, encoding="utf-8")
    logger.info("cfpb_extract complete — %s (%d records)", out_path, len(pdf))


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

"""Converted from talend_jobs/loan_processing/loan_application_ingest_0.1.item.

Flow: tFileInputDelimited(daily_loan_applications.csv) → tMap(calculate
      monthly payment, DTI ratio, LTV ratio, format currency)
      → tDBOutput(Snowflake STG_LOAN_APPLICATION)

Source: CSV file  |  Target: Snowflake RAW.STG_LOAN_APPLICATION
Custom routines: AmountUtils
"""
import logging
import math

import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    format_currency,
    round_to_decimal,
)

logger = logging.getLogger("etl.loan_application_ingest")


def run(session: Session, config: dict) -> None:
    input_dir = config.get("input_dir", "/data/incoming/loan_apps/")
    tgt_schema = config.get("tgt_schema", "RAW")

    # tFileInputDelimited_1: read CSV
    filepath = f"{input_dir}daily_loan_applications.csv"
    pdf = pd.read_csv(filepath, encoding="utf-8", dtype={
        "APPLICATION_ID": str,
        "CUSTOMER_ID": str,
    })

    # tMap_1: compute derived fields row by row
    rows = []
    for _, r in pdf.iterrows():
        monthly = calculate_monthly_payment(
            r["REQUESTED_AMOUNT"], r.get("INTEREST_RATE", 0) or 0, int(r["TERM_MONTHS"])
        )
        annual_income = r["ANNUAL_INCOME"]
        dti = (monthly * 12) / annual_income if annual_income > 0 else 0.0
        collateral = r.get("COLLATERAL_VALUE")
        ltv = (
            r["REQUESTED_AMOUNT"] / collateral
            if collateral and not math.isnan(collateral) and collateral > 0
            else None
        )
        rows.append({
            "APPLICATION_ID": r["APPLICATION_ID"],
            "CUSTOMER_ID": r["CUSTOMER_ID"],
            "LOAN_TYPE": str(r["LOAN_TYPE"]).upper().strip(),
            "REQUESTED_AMOUNT": r["REQUESTED_AMOUNT"],
            "FORMATTED_AMOUNT": format_currency(r["REQUESTED_AMOUNT"]),
            "TERM_MONTHS": int(r["TERM_MONTHS"]),
            "INTEREST_RATE": r.get("INTEREST_RATE"),
            "DTI_RATIO": round_to_decimal(dti, 4),
            "LTV_RATIO": round_to_decimal(ltv, 4) if ltv is not None else None,
            "APPLICATION_DATE": str(r["APPLICATION_DATE"]),
        })

    df = session.create_dataframe(rows)
    df = df.with_column("INGESTED_AT", F.current_timestamp())

    # tDBOutput_1: INSERT to STG_LOAN_APPLICATION
    df.write.mode("append").save_as_table(f"{tgt_schema}.STG_LOAN_APPLICATION")
    logger.info("loan_application_ingest complete — %d records", len(rows))


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

"""Converted from: talend_jobs/loan_processing/loan_application_ingest_0.1.item

Reads daily loan applications from CSV, calculates DTI/LTV ratios and
formatted amounts, loads to Snowflake staging.

Components: tFileInputDelimited → tMap → tDBOutput(Snowflake)
Routines:   AmountUtils
"""
import logging

import pandas as pd
from snowflake.snowpark import Session

from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    format_currency,
    round_to_decimal,
)

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    input_dir = config.get("input_dir", "/data/incoming/loan_apps/")
    filepath = f"{input_dir}daily_loan_applications.csv"

    df_pd = pd.read_csv(
        filepath,
        encoding="utf-8",
        dtype={"APPLICATION_ID": str, "CUSTOMER_ID": str},
    )

    rows = []
    for _, r in df_pd.iterrows():
        monthly_payment = calculate_monthly_payment(
            float(r["REQUESTED_AMOUNT"]),
            float(r["INTEREST_RATE"]) if pd.notna(r.get("INTEREST_RATE")) else 0.0,
            int(r["TERM_MONTHS"]),
        )
        annual_income = float(r["ANNUAL_INCOME"])
        dti_ratio = (
            (monthly_payment * 12) / annual_income if annual_income > 0 else 0.0
        )
        collateral_value = (
            float(r["COLLATERAL_VALUE"])
            if pd.notna(r.get("COLLATERAL_VALUE")) and float(r["COLLATERAL_VALUE"]) > 0
            else None
        )
        ltv_ratio = (
            float(r["REQUESTED_AMOUNT"]) / collateral_value
            if collateral_value
            else None
        )
        rows.append({
            "APPLICATION_ID": r["APPLICATION_ID"],
            "CUSTOMER_ID": r["CUSTOMER_ID"],
            "LOAN_TYPE": str(r["LOAN_TYPE"]).upper().strip(),
            "REQUESTED_AMOUNT": float(r["REQUESTED_AMOUNT"]),
            "FORMATTED_AMOUNT": format_currency(float(r["REQUESTED_AMOUNT"])),
            "TERM_MONTHS": int(r["TERM_MONTHS"]),
            "INTEREST_RATE": (
                float(r["INTEREST_RATE"]) if pd.notna(r.get("INTEREST_RATE")) else None
            ),
            "DTI_RATIO": round_to_decimal(dti_ratio, 4),
            "LTV_RATIO": (
                round_to_decimal(ltv_ratio, 4) if ltv_ratio is not None else None
            ),
            "APPLICATION_DATE": str(r["APPLICATION_DATE"]),
        })

    df_snow = session.create_dataframe(rows)
    row_count = df_snow.count()
    df_snow.write.mode("append").save_as_table(
        f"{config.get('tgt_schema', 'RAW')}.STG_LOAN_APPLICATION"
    )
    logger.info("loan_application_ingest: loaded %d rows", row_count)
    return row_count

"""Converted from talend_jobs/payment_reconciliation/payment_discrepancy_0.1.item.

Flow: tDBInput(Snowflake PAYMENT_RECONCILIATION unmatched)
      → tMap(format currency amounts) → tFileOutputDelimited(CSV report)

Source: Snowflake PAYMENT_RECONCILIATION  |  Target: CSV file
Custom routines: AmountUtils
"""
import logging

import pandas as pd
from snowflake.snowpark import Session

from python_target.routines.amount_utils import format_currency

logger = logging.getLogger("etl.payment_discrepancy")


def run(session: Session, config: dict) -> None:
    output_dir = config.get("output_dir", "/data/reports/discrepancies/")
    report_date = config.get("report_date", "")

    # tDBInput_1: unmatched payments from reconciliation
    df = session.sql("""
        SELECT PAYMENT_ID, LOAN_ID, CUSTOMER_ID, PAYMENT_AMOUNT,
               AMOUNT_DUE, VARIANCE, MATCH_STATUS, RECONCILED_AT
        FROM PAYMENT_RECONCILIATION
        WHERE MATCH_STATUS != 'MATCHED'
          AND RECONCILED_AT >= DATEADD(day, -1, CURRENT_DATE())
    """)

    # tMap_1: format currency for report
    pdf = df.to_pandas()
    pdf["PAYMENT_AMOUNT"] = pdf["PAYMENT_AMOUNT"].apply(lambda x: format_currency(x) if pd.notna(x) else "")
    pdf["AMOUNT_DUE"] = pdf["AMOUNT_DUE"].apply(lambda x: format_currency(x) if pd.notna(x) else "")
    pdf["VARIANCE"] = pdf["VARIANCE"].apply(lambda x: format_currency(x) if pd.notna(x) else "")
    pdf = pdf.rename(columns={"MATCH_STATUS": "DISCREPANCY_TYPE"})
    pdf["REPORT_DATE"] = report_date

    out_cols = [
        "PAYMENT_ID", "LOAN_ID", "CUSTOMER_ID", "PAYMENT_AMOUNT",
        "AMOUNT_DUE", "VARIANCE", "DISCREPANCY_TYPE", "REPORT_DATE",
    ]

    # tFileOutputDelimited_1: CSV output
    out_path = f"{output_dir}discrepancy_report_{report_date}.csv"
    pdf[out_cols].to_csv(out_path, index=False, encoding="utf-8")
    logger.info("payment_discrepancy complete — %s (%d rows)", out_path, len(pdf))


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

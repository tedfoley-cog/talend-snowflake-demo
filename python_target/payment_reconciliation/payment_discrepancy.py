"""Converted from: talend_jobs/payment_reconciliation/payment_discrepancy_0.1.item

Reads unmatched payments from PAYMENT_RECONCILIATION, formats currency
amounts, and writes a discrepancy report CSV.

Components: tDBInput(Snowflake) → tMap → tFileOutputDelimited
Routines:   AmountUtils
"""
import logging

from snowflake.snowpark import Session

from python_target.routines.amount_utils import format_currency

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    report_date = config.get("report_date", "")
    output_dir = config.get("output_dir", "/data/reports/discrepancies/")

    df = session.sql("""
        SELECT PAYMENT_ID, LOAN_ID, CUSTOMER_ID, PAYMENT_AMOUNT,
               AMOUNT_DUE, VARIANCE, MATCH_STATUS, RECONCILED_AT
        FROM PAYMENT_RECONCILIATION
        WHERE MATCH_STATUS != 'MATCHED'
          AND RECONCILED_AT >= DATEADD(day, -1, CURRENT_DATE())
    """)

    rows = df.collect()
    report_rows = []
    for r in rows:
        report_rows.append({
            "PAYMENT_ID": r["PAYMENT_ID"],
            "LOAN_ID": r["LOAN_ID"],
            "CUSTOMER_ID": r["CUSTOMER_ID"],
            "PAYMENT_AMOUNT": format_currency(float(r["PAYMENT_AMOUNT"])),
            "AMOUNT_DUE": format_currency(float(r["AMOUNT_DUE"])),
            "VARIANCE": format_currency(float(r["VARIANCE"])),
            "DISCREPANCY_TYPE": r["MATCH_STATUS"],
            "REPORT_DATE": report_date,
        })

    if report_rows:
        import pandas as pd

        df_report = pd.DataFrame(report_rows)
        output_path = f"{output_dir}discrepancy_report_{report_date}.csv"
        df_report.to_csv(output_path, index=False, encoding="utf-8")
        logger.info(
            "payment_discrepancy: wrote %d rows to %s",
            len(report_rows),
            output_path,
        )
    else:
        logger.info("payment_discrepancy: no discrepancies found")

    return len(report_rows)

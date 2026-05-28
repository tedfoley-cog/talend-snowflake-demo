"""Converted from talend_jobs/payment_reconciliation/payment_match_0.1.item.

Flow: tDBInput_1(Oracle INCOMING_PAYMENTS) + tDBInput_2(Oracle LOAN_BALANCE)
      → tMap(LEFT JOIN on LOAN_ID, compute variance, classify match status)
      → tDBOutput(Snowflake PAYMENT_RECONCILIATION)

Source: Oracle 12c  |  Target: Snowflake PAYMENT_RECONCILIATION
Custom routines: AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.payment_match")


def run(session: Session, config: dict) -> None:
    recon_date = config.get("recon_date", "")
    match_tolerance = float(config.get("match_tolerance", 0.01))

    # tDBInput_1: incoming payments
    df_payments = session.sql(f"""
        SELECT PAYMENT_ID, LOAN_ID, CUSTOMER_ID, PAYMENT_AMOUNT,
               PAYMENT_DATE, PAYMENT_METHOD, REFERENCE_NUM
        FROM INCOMING_PAYMENTS
        WHERE PAYMENT_DATE = TO_DATE('{recon_date}', 'YYYY-MM-DD')
          AND RECONCILED = 'N'
    """)

    # tDBInput_2: outstanding balances
    df_balances = session.sql(f"""
        SELECT LOAN_ID, CUSTOMER_ID, OUTSTANDING_BALANCE,
               MONTHLY_PAYMENT_DUE, DUE_DATE, DAYS_PAST_DUE
        FROM LOAN_BALANCE
        WHERE DUE_DATE <= TO_DATE('{recon_date}', 'YYYY-MM-DD')
    """)

    # tMap_1: LEFT JOIN on LOAN_ID
    df = df_payments.join(df_balances, on="LOAN_ID", how="left", lsuffix="_pay", rsuffix="_bal")

    # Variance calculation
    df = df.with_column(
        "VARIANCE",
        F.round(F.abs(F.col("PAYMENT_AMOUNT") - F.col("MONTHLY_PAYMENT_DUE")), 2),
    )

    # Match status classification
    tol = F.lit(match_tolerance)
    df = df.with_column(
        "MATCH_STATUS",
        F.when(F.col("MONTHLY_PAYMENT_DUE").is_null(), F.lit("UNMATCHED"))
        .when(F.col("VARIANCE") <= tol, F.lit("MATCHED"))
        .when(F.col("PAYMENT_AMOUNT") > F.col("MONTHLY_PAYMENT_DUE") + tol, F.lit("OVERPAYMENT"))
        .otherwise(F.lit("UNDERPAYMENT")),
    )

    df = df.with_column(
        "AMOUNT_DUE", F.round(F.col("MONTHLY_PAYMENT_DUE"), 2)
    )
    df = df.with_column(
        "PAYMENT_AMOUNT", F.round(F.col("PAYMENT_AMOUNT"), 2)
    )
    df = df.with_column("RECONCILED_AT", F.current_timestamp())

    df_out = df.select(
        "PAYMENT_ID", "LOAN_ID", F.col("CUSTOMER_ID_pay").alias("CUSTOMER_ID"),
        "PAYMENT_AMOUNT", "AMOUNT_DUE", "VARIANCE", "MATCH_STATUS", "RECONCILED_AT",
    )

    # tDBOutput_1: INSERT to PAYMENT_RECONCILIATION
    df_out.write.mode("append").save_as_table("PAYMENT_RECONCILIATION")
    logger.info("payment_match complete")


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

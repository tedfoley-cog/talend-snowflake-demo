"""Converted from: talend_jobs/payment_reconciliation/payment_match_0.1.item

Matches incoming payments against outstanding loan balances via
left join on LOAN_ID. Classifies each payment as MATCHED,
OVERPAYMENT, or UNDERPAYMENT based on configurable tolerance.

Components: tDBInput(Oracle)[x2] → tMap(join on LOAN_ID) → tDBOutput(Snowflake)
Routines:   AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

from python_target.routines.amount_utils import round_to_decimal  # noqa: F401

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    recon_date = config.get("recon_date")
    tolerance = config.get("match_tolerance", 0.01)

    date_expr = (
        f"TO_DATE('{recon_date}', 'YYYY-MM-DD')" if recon_date else "CURRENT_DATE()"
    )

    df_payments = session.sql(f"""
        SELECT PAYMENT_ID, LOAN_ID, CUSTOMER_ID, PAYMENT_AMOUNT,
               PAYMENT_DATE, PAYMENT_METHOD, REFERENCE_NUM
        FROM INCOMING_PAYMENTS
        WHERE PAYMENT_DATE = {date_expr}
          AND RECONCILED = 'N'
    """)

    df_balances = session.sql(f"""
        SELECT LOAN_ID, CUSTOMER_ID, OUTSTANDING_BALANCE,
               MONTHLY_PAYMENT_DUE, DUE_DATE, DAYS_PAST_DUE
        FROM LOAN_BALANCE
        WHERE DUE_DATE <= {date_expr}
    """)

    # tMap: left join on LOAN_ID
    df_joined = df_payments.join(
        df_balances,
        on="LOAN_ID",
        how="left",
        lsuffix="_pay",
        rsuffix="_bal",
    )

    df_result = df_joined.select(
        F.col("PAYMENT_ID"),
        F.col("LOAN_ID"),
        df_payments["CUSTOMER_ID"].alias("CUSTOMER_ID"),
        F.round(F.col("PAYMENT_AMOUNT"), 2).alias("PAYMENT_AMOUNT"),
        F.round(F.col("MONTHLY_PAYMENT_DUE"), 2).alias("AMOUNT_DUE"),
        F.round(
            F.abs(F.col("PAYMENT_AMOUNT") - F.col("MONTHLY_PAYMENT_DUE")), 2
        ).alias("VARIANCE"),
        F.when(
            F.abs(F.col("PAYMENT_AMOUNT") - F.col("MONTHLY_PAYMENT_DUE"))
            <= F.lit(tolerance),
            F.lit("MATCHED"),
        )
        .when(
            F.col("PAYMENT_AMOUNT")
            > F.col("MONTHLY_PAYMENT_DUE") + F.lit(tolerance),
            F.lit("OVERPAYMENT"),
        )
        .otherwise(F.lit("UNDERPAYMENT"))
        .alias("MATCH_STATUS"),
        F.current_timestamp().alias("RECONCILED_AT"),
    )

    row_count = df_result.count()
    df_result.write.mode("append").save_as_table("PAYMENT_RECONCILIATION")
    logger.info("payment_match: reconciled %d payments", row_count)
    return row_count

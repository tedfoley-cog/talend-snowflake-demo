"""Converted from: talend_jobs/loan_processing/loan_risk_scoring_0.1.item

Scores pending loan applications with a composite risk model
(credit 40%, employment 20%, DTI 40%). Assigns risk tier and
auto-decision. Loads results to LOAN_RISK_SCORES.

Components: tDBInput(Oracle) → tMap → tDBOutput(Snowflake)
Routines:   AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    round_to_decimal,
)

logger = logging.getLogger("etl")


def _score_row(row: dict, risk_model_version: str) -> dict:
    annual_income = row["ANNUAL_INCOME"]
    monthly_pmt = calculate_monthly_payment(
        row["REQUESTED_AMOUNT"],
        row["INTEREST_RATE"] or 0.0,
        row["TERM_MONTHS"],
    )
    existing_debt = row.get("EXISTING_DEBT") or 0.0
    dti = (
        ((monthly_pmt * 12) + existing_debt) / annual_income
        if annual_income > 0
        else 999.0
    )

    collateral = row.get("COLLATERAL_VALUE")
    ltv = (
        row["REQUESTED_AMOUNT"] / collateral
        if collateral and collateral > 0
        else None
    )

    credit = row["CREDIT_SCORE"]
    credit_factor = 100 if credit >= 750 else (75 if credit >= 700 else (50 if credit >= 650 else 25))

    emp_years = row.get("EMPLOYMENT_YEARS")
    emp_factor = (
        100 if emp_years and emp_years >= 5
        else (75 if emp_years and emp_years >= 2 else 50)
    )

    dti_factor = (
        100 if dti < 0.36
        else (75 if dti < 0.43 else (50 if dti < 0.50 else 25))
    )

    composite = int(credit_factor * 0.40 + emp_factor * 0.20 + dti_factor * 0.40)
    risk_tier = "LOW" if composite >= 80 else ("MEDIUM" if composite >= 60 else "HIGH")
    decision = (
        "AUTO_APPROVE" if composite >= 70
        else ("MANUAL_REVIEW" if composite >= 50 else "AUTO_DECLINE")
    )
    factors = (
        f"credit={credit_factor};employment={emp_factor};"
        f"dti={dti_factor};model={risk_model_version}"
    )

    return {
        "APPLICATION_ID": row["APPLICATION_ID"],
        "CUSTOMER_ID": row["CUSTOMER_ID"],
        "RISK_SCORE": composite,
        "RISK_TIER": risk_tier,
        "DTI_RATIO": round_to_decimal(dti, 4),
        "LTV_RATIO": round_to_decimal(ltv, 4) if ltv is not None else None,
        "DECISION": decision,
        "DECISION_FACTORS": factors,
    }


def run(session: Session, config: dict) -> int:
    risk_model_version = config.get("risk_model_version", "v3.2")

    df = session.sql("""
        SELECT
            la.APPLICATION_ID, la.CUSTOMER_ID, la.LOAN_TYPE,
            la.REQUESTED_AMOUNT, la.TERM_MONTHS, la.INTEREST_RATE,
            la.ANNUAL_INCOME, la.CREDIT_SCORE, la.EMPLOYMENT_YEARS,
            la.EXISTING_DEBT, la.COLLATERAL_VALUE,
            cm.ACCOUNT_STATUS, cm.CUSTOMER_SINCE
        FROM LOAN_APPLICATION la
        JOIN CUSTOMER_MASTER cm ON la.CUSTOMER_ID = cm.CUSTOMER_ID
        WHERE la.STATUS = 'PENDING_REVIEW'
    """)

    rows = df.collect()
    scored = [_score_row(r.as_dict(), risk_model_version) for r in rows]

    if not scored:
        logger.info("loan_risk_scoring: no pending applications")
        return 0

    schema = StructType([
        StructField("APPLICATION_ID", StringType()),
        StructField("CUSTOMER_ID", StringType()),
        StructField("RISK_SCORE", IntegerType()),
        StructField("RISK_TIER", StringType()),
        StructField("DTI_RATIO", DoubleType()),
        StructField("LTV_RATIO", DoubleType()),
        StructField("DECISION", StringType()),
        StructField("DECISION_FACTORS", StringType()),
    ])
    df_out = session.create_dataframe(scored, schema=schema)
    df_out = df_out.with_column("SCORED_AT", F.current_timestamp())

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table("LOAN_RISK_SCORES")
    logger.info("loan_risk_scoring: scored %d applications", row_count)
    return row_count

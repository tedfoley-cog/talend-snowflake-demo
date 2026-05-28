"""Converted from talend_jobs/loan_processing/loan_risk_scoring_0.1.item.

Flow: tDBInput(Oracle LOAN_APPLICATION JOIN CUSTOMER_MASTER) → tMap(DTI,
      LTV, credit/employment/DTI factors, composite score, risk tier,
      decision) → tDBOutput(Snowflake LOAN_RISK_SCORES INSERT_OR_UPDATE)

Source: Oracle 12c  |  Target: Snowflake LOAN_RISK_SCORES
Custom routines: AmountUtils
"""
import logging

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.loan_risk_scoring")


def run(session: Session, config: dict) -> None:
    risk_model_version = config.get("risk_model_version", "v3.2")

    # tDBInput_1: pending loan applications joined with customer data
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

    # tMap_1 var table: risk calculations via Snowpark functions
    # DTI ratio
    df = df.with_column(
        "DTI_RATIO",
        F.when(
            F.col("ANNUAL_INCOME") > 0,
            F.round(
                (
                    (F.col("REQUESTED_AMOUNT") * F.col("INTEREST_RATE") / F.lit(100.0) / F.lit(12.0))
                    + F.coalesce(F.col("EXISTING_DEBT"), F.lit(0))
                ) / F.col("ANNUAL_INCOME"),
                4,
            ),
        ).otherwise(F.lit(999)),
    )

    # LTV ratio
    df = df.with_column(
        "LTV_RATIO",
        F.when(
            F.col("COLLATERAL_VALUE").is_not_null() & (F.col("COLLATERAL_VALUE") > 0),
            F.round(F.col("REQUESTED_AMOUNT") / F.col("COLLATERAL_VALUE"), 4),
        ),
    )

    # Credit factor
    df = df.with_column(
        "CREDIT_FACTOR",
        F.when(F.col("CREDIT_SCORE") >= 750, F.lit(100))
        .when(F.col("CREDIT_SCORE") >= 700, F.lit(75))
        .when(F.col("CREDIT_SCORE") >= 650, F.lit(50))
        .otherwise(F.lit(25)),
    )

    # Employment factor
    df = df.with_column(
        "EMPLOYMENT_FACTOR",
        F.when(
            F.col("EMPLOYMENT_YEARS").is_not_null() & (F.col("EMPLOYMENT_YEARS") >= 5),
            F.lit(100),
        )
        .when(
            F.col("EMPLOYMENT_YEARS").is_not_null() & (F.col("EMPLOYMENT_YEARS") >= 2),
            F.lit(75),
        )
        .otherwise(F.lit(50)),
    )

    # DTI factor
    df = df.with_column(
        "DTI_FACTOR",
        F.when(F.col("DTI_RATIO") < 0.36, F.lit(100))
        .when(F.col("DTI_RATIO") < 0.43, F.lit(75))
        .when(F.col("DTI_RATIO") < 0.50, F.lit(50))
        .otherwise(F.lit(25)),
    )

    # Composite score
    df = df.with_column(
        "RISK_SCORE",
        F.floor(
            F.col("CREDIT_FACTOR") * 0.40
            + F.col("EMPLOYMENT_FACTOR") * 0.20
            + F.col("DTI_FACTOR") * 0.40
        ).cast("INT"),
    )

    # Risk tier
    df = df.with_column(
        "RISK_TIER",
        F.when(F.col("RISK_SCORE") >= 80, F.lit("LOW"))
        .when(F.col("RISK_SCORE") >= 60, F.lit("MEDIUM"))
        .otherwise(F.lit("HIGH")),
    )

    # Decision
    df = df.with_column(
        "DECISION",
        F.when(F.col("RISK_SCORE") >= 70, F.lit("AUTO_APPROVE"))
        .when(F.col("RISK_SCORE") >= 50, F.lit("MANUAL_REVIEW"))
        .otherwise(F.lit("AUTO_DECLINE")),
    )

    # Decision factors
    df = df.with_column(
        "DECISION_FACTORS",
        F.concat(
            F.lit("credit="), F.col("CREDIT_FACTOR").cast("STRING"),
            F.lit(";employment="), F.col("EMPLOYMENT_FACTOR").cast("STRING"),
            F.lit(";dti="), F.col("DTI_FACTOR").cast("STRING"),
            F.lit(f";model={risk_model_version}"),
        ),
    )

    df = df.with_column("SCORED_AT", F.current_timestamp())

    df_out = df.select(
        "APPLICATION_ID", "CUSTOMER_ID", "RISK_SCORE", "RISK_TIER",
        "DTI_RATIO", "LTV_RATIO", "DECISION", "DECISION_FACTORS", "SCORED_AT",
    )

    # tDBOutput_1: INSERT_OR_UPDATE → stage to temp table then MERGE
    df_out.write.mode("overwrite").save_as_table("__LOAN_RISK_SCORES_STG")

    session.sql("""
        MERGE INTO LOAN_RISK_SCORES tgt
        USING __LOAN_RISK_SCORES_STG src ON tgt.APPLICATION_ID = src.APPLICATION_ID
        WHEN MATCHED THEN UPDATE SET
            tgt.RISK_SCORE = src.RISK_SCORE,
            tgt.RISK_TIER = src.RISK_TIER,
            tgt.DTI_RATIO = src.DTI_RATIO,
            tgt.LTV_RATIO = src.LTV_RATIO,
            tgt.DECISION = src.DECISION,
            tgt.DECISION_FACTORS = src.DECISION_FACTORS,
            tgt.SCORED_AT = src.SCORED_AT
        WHEN NOT MATCHED THEN INSERT (
            APPLICATION_ID, CUSTOMER_ID, RISK_SCORE, RISK_TIER,
            DTI_RATIO, LTV_RATIO, DECISION, DECISION_FACTORS, SCORED_AT
        ) VALUES (
            src.APPLICATION_ID, src.CUSTOMER_ID, src.RISK_SCORE, src.RISK_TIER,
            src.DTI_RATIO, src.LTV_RATIO, src.DECISION, src.DECISION_FACTORS,
            src.SCORED_AT
        )
    """).collect()
    logger.info("loan_risk_scoring complete")


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

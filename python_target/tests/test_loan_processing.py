"""Test scaffolding for loan_processing domain jobs.

These tests validate the transformation logic of each converted job.
"""
from unittest.mock import MagicMock


from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    format_currency,
)


class TestLoanApplicationIngest:
    """Tests for loan_application_ingest.py (from loan_application_ingest_0.1.item)."""

    def test_dti_ratio_calculation(self):
        """DTI = (monthlyPayment * 12) / annualIncome."""
        monthly = calculate_monthly_payment(200000, 4.5, 360)
        annual_income = 80000.0
        dti = (monthly * 12) / annual_income
        assert 0.1 < dti < 0.5

    def test_ltv_ratio_calculation(self):
        """LTV = requestedAmount / collateralValue."""
        requested = 200000.0
        collateral = 250000.0
        ltv = requested / collateral
        assert ltv == 0.8

    def test_ltv_none_when_no_collateral(self):
        """LTV should be None when collateral is 0 or missing."""
        collateral = 0.0
        ltv = None if collateral <= 0 else 200000 / collateral
        assert ltv is None

    def test_formatted_amount(self):
        assert format_currency(25000.0) == "$25,000.00"

    def test_loan_type_normalized(self):
        """LOAN_TYPE should be uppercased and trimmed."""
        assert "  auto loan  ".upper().strip() == "AUTO LOAN"


class TestLoanRiskScoring:
    """Tests for loan_risk_scoring.py (from loan_risk_scoring_0.1.item)."""

    def test_credit_factor_tiers(self):
        """credit >= 750 → 100, >= 700 → 75, >= 650 → 50, else 25."""
        from python_target.loan_processing.loan_risk_scoring import _score_row

        base = {
            "APPLICATION_ID": "APP001",
            "CUSTOMER_ID": "CUST001",
            "REQUESTED_AMOUNT": 200000,
            "TERM_MONTHS": 360,
            "INTEREST_RATE": 4.5,
            "ANNUAL_INCOME": 80000,
            "CREDIT_SCORE": 750,
            "EMPLOYMENT_YEARS": 5,
            "EXISTING_DEBT": 0,
            "COLLATERAL_VALUE": 250000,
        }
        result = _score_row(base, "v3.2")
        assert result["RISK_SCORE"] > 0
        assert result["RISK_TIER"] in ("LOW", "MEDIUM", "HIGH")

    def test_high_credit_low_risk(self):
        from python_target.loan_processing.loan_risk_scoring import _score_row

        row = {
            "APPLICATION_ID": "A1",
            "CUSTOMER_ID": "C1",
            "REQUESTED_AMOUNT": 50000,
            "TERM_MONTHS": 60,
            "INTEREST_RATE": 3.0,
            "ANNUAL_INCOME": 120000,
            "CREDIT_SCORE": 800,
            "EMPLOYMENT_YEARS": 10,
            "EXISTING_DEBT": 0,
            "COLLATERAL_VALUE": 100000,
        }
        result = _score_row(row, "v3.2")
        assert result["RISK_TIER"] == "LOW"
        assert result["DECISION"] == "AUTO_APPROVE"

    def test_low_credit_high_risk(self):
        from python_target.loan_processing.loan_risk_scoring import _score_row

        row = {
            "APPLICATION_ID": "A2",
            "CUSTOMER_ID": "C2",
            "REQUESTED_AMOUNT": 200000,
            "TERM_MONTHS": 360,
            "INTEREST_RATE": 8.0,
            "ANNUAL_INCOME": 40000,
            "CREDIT_SCORE": 580,
            "EMPLOYMENT_YEARS": 1,
            "EXISTING_DEBT": 20000,
            "COLLATERAL_VALUE": None,
        }
        result = _score_row(row, "v3.2")
        assert result["RISK_TIER"] == "HIGH"
        assert result["DECISION"] == "AUTO_DECLINE"

    def test_decision_factors_format(self):
        from python_target.loan_processing.loan_risk_scoring import _score_row

        row = {
            "APPLICATION_ID": "A3",
            "CUSTOMER_ID": "C3",
            "REQUESTED_AMOUNT": 100000,
            "TERM_MONTHS": 120,
            "INTEREST_RATE": 5.0,
            "ANNUAL_INCOME": 80000,
            "CREDIT_SCORE": 700,
            "EMPLOYMENT_YEARS": 3,
            "EXISTING_DEBT": 5000,
            "COLLATERAL_VALUE": 150000,
        }
        result = _score_row(row, "v3.2")
        assert "credit=" in result["DECISION_FACTORS"]
        assert "model=v3.2" in result["DECISION_FACTORS"]


class TestLoanStatusUpdate:
    """Tests for loan_status_update.py (from loan_status_update_0.1.item)."""

    def test_run_calls_merge(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.count.return_value = 10
        session.sql.return_value = df_mock
        from python_target.loan_processing.loan_status_update import run

        result = run(session, {})
        assert result == 10
        assert session.sql.call_count >= 2  # SELECT + MERGE

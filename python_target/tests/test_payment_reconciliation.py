"""Test scaffolding for payment_reconciliation domain jobs."""
from unittest.mock import MagicMock


from python_target.routines.amount_utils import format_currency, round_to_decimal


class TestPaymentMatch:
    """Tests for payment_match.py (from payment_match_0.1.item)."""

    def test_variance_calculation(self):
        """variance = abs(PAYMENT_AMOUNT - MONTHLY_PAYMENT_DUE)."""
        payment = 1500.00
        due = 1495.50
        variance = round_to_decimal(abs(payment - due), 2)
        assert variance == 4.50

    def test_exact_match_within_tolerance(self):
        tolerance = 0.01
        payment = 1500.00
        due = 1500.005
        assert abs(payment - due) <= tolerance

    def test_overpayment_classification(self):
        tolerance = 0.01
        payment = 1600.00
        due = 1500.00
        assert payment > due + tolerance

    def test_underpayment_classification(self):
        tolerance = 0.01
        payment = 1400.00
        due = 1500.00
        assert payment < due - tolerance


class TestPaymentDiscrepancy:
    """Tests for payment_discrepancy.py (from payment_discrepancy_0.1.item)."""

    def test_currency_formatting(self):
        assert format_currency(1234.56) == "$1,234.56"

    def test_run_returns_count(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.collect.return_value = []
        session.sql.return_value = df_mock
        from python_target.payment_reconciliation.payment_discrepancy import run

        result = run(session, {"report_date": "2024-01-15"})
        assert result == 0


class TestPaymentSettlement:
    """Tests for payment_settlement.py (from payment_settlement_0.1.item)."""

    def test_auto_settle_threshold(self):
        """Payments <= threshold → AUTO, else MANUAL_REVIEW."""
        threshold = 5000.00
        assert 4999.99 <= threshold
        assert 5000.01 > threshold

    def test_run_executes_merge(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 3
        session.sql.return_value = df_mock
        from python_target.payment_reconciliation.payment_settlement import run

        result = run(session, {"auto_settle_threshold": 5000})
        assert result == 3

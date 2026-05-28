"""Unit tests for python_target/routines/amount_utils.py."""

from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    cents_to_dollars,
    is_valid_amount,
    round_to_decimal,
)


class TestRoundToDecimal:
    def test_rounds_half_up(self):
        assert round_to_decimal(1.005, 2) == 1.01

    def test_rounds_down(self):
        assert round_to_decimal(1.004, 2) == 1.00

    def test_integer(self):
        assert round_to_decimal(5.0, 0) == 5.0


class TestCalculateMonthlyPayment:
    def test_standard_loan(self):
        result = calculate_monthly_payment(100000, 6.0, 360)
        assert 599.0 < result < 600.0

    def test_zero_rate(self):
        result = calculate_monthly_payment(12000, 0.0, 12)
        assert result == 1000.0

    def test_zero_amount(self):
        assert calculate_monthly_payment(0, 5.0, 12) == 0.0

    def test_zero_term(self):
        assert calculate_monthly_payment(10000, 5.0, 0) == 0.0


class TestIsValidAmount:
    def test_valid(self):
        assert is_valid_amount(100.0, 1000.0) is True

    def test_negative(self):
        assert is_valid_amount(-1.0, 1000.0) is False

    def test_exceeds_max(self):
        assert is_valid_amount(2000.0, 1000.0) is False

    def test_nan(self):
        assert is_valid_amount(float("nan"), 1000.0) is False


class TestCentsToDollars:
    def test_simple(self):
        assert cents_to_dollars(1050) == 10.50

    def test_zero(self):
        assert cents_to_dollars(0) == 0.00

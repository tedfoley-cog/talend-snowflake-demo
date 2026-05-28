"""Unit tests for routines/amount_utils.py (converted from AmountUtils.java)."""
import math


from python_target.routines.amount_utils import (
    calculate_monthly_payment,
    cents_to_dollars,
    format_currency,
    is_valid_amount,
    round_to_decimal,
)


class TestRoundToDecimal:
    def test_round_half_up(self):
        assert round_to_decimal(1.235, 2) == 1.24

    def test_round_two_places(self):
        assert round_to_decimal(45000.5, 2) == 45000.50

    def test_round_four_places(self):
        assert round_to_decimal(0.43219, 4) == 0.4322


class TestFormatCurrency:
    def test_basic_format(self):
        result = format_currency(45000.5)
        assert result == "$45,000.50"

    def test_zero(self):
        assert format_currency(0) == "$0.00"

    def test_negative(self):
        result = format_currency(-1234.56)
        assert "-" in result and "1,234.56" in result


class TestCalculateMonthlyPayment:
    def test_standard_loan(self):
        payment = calculate_monthly_payment(200000, 4.5, 360)
        assert 1000 < payment < 1100

    def test_zero_amount(self):
        assert calculate_monthly_payment(0, 5, 60) == 0.0

    def test_zero_term(self):
        assert calculate_monthly_payment(10000, 5, 0) == 0.0

    def test_zero_rate(self):
        assert calculate_monthly_payment(12000, 0, 12) == 1000.0

    def test_negative_rate(self):
        assert calculate_monthly_payment(12000, -1, 12) == 1000.0


class TestIsValidAmount:
    def test_valid(self):
        assert is_valid_amount(100, 10000) is True

    def test_zero(self):
        assert is_valid_amount(0, 10000) is False

    def test_negative(self):
        assert is_valid_amount(-5, 10000) is False

    def test_exceeds_max(self):
        assert is_valid_amount(10001, 10000) is False

    def test_nan(self):
        assert is_valid_amount(float("nan"), 10000) is False

    def test_inf(self):
        assert is_valid_amount(math.inf, 10000) is False


class TestCentsToDollars:
    def test_conversion(self):
        assert cents_to_dollars(4500) == 45.00

    def test_odd_cents(self):
        assert cents_to_dollars(199) == 1.99

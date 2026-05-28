"""Converted from routines/AmountUtils.java.

Currency rounding, formatting, and amortization calculations.
"""
import locale
import math
from decimal import ROUND_HALF_UP, Decimal


def round_to_decimal(value: float, places: int) -> float:
    d = Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    return float(d)


def format_currency(amount: float) -> str:
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except locale.Error:
        pass
    return locale.currency(amount, grouping=True)


def calculate_monthly_payment(
    loan_amount: float, annual_rate: float, term_months: int
) -> float:
    if loan_amount <= 0 or term_months <= 0:
        return 0.0
    if annual_rate <= 0:
        return loan_amount / term_months
    monthly_rate = annual_rate / 100.0 / 12.0
    factor = math.pow(1 + monthly_rate, term_months)
    return round_to_decimal(loan_amount * (monthly_rate * factor) / (factor - 1), 2)


def is_valid_amount(amount: float, max_allowed: float) -> bool:
    return (
        amount > 0
        and amount <= max_allowed
        and not math.isnan(amount)
        and not math.isinf(amount)
    )


def cents_to_dollars(cents: int) -> float:
    return round_to_decimal(cents / 100.0, 2)

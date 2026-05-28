"""Unit tests for routines/validators.py (converted from AccountValidator.java)."""

from python_target.routines.validators import (
    format_ssn,
    is_valid_account_number,
    is_valid_ssn,
    luhn_check,
    mask_field,
)


class TestIsValidSSN:
    def test_valid_formatted(self):
        assert is_valid_ssn("123-45-6789") is True

    def test_valid_numeric(self):
        assert is_valid_ssn("123456789") is True

    def test_none(self):
        assert is_valid_ssn(None) is False

    def test_empty(self):
        assert is_valid_ssn("") is False

    def test_area_000(self):
        assert is_valid_ssn("000-12-3456") is False

    def test_area_666(self):
        assert is_valid_ssn("666-12-3456") is False

    def test_area_9xx(self):
        assert is_valid_ssn("900-12-3456") is False

    def test_group_00(self):
        assert is_valid_ssn("123-00-6789") is False

    def test_serial_0000(self):
        assert is_valid_ssn("123-45-0000") is False

    def test_too_short(self):
        assert is_valid_ssn("12345") is False


class TestFormatSSN:
    def test_numeric_to_formatted(self):
        assert format_ssn("123456789") == "123-45-6789"

    def test_already_formatted(self):
        assert format_ssn("123-45-6789") == "123-45-6789"

    def test_none(self):
        assert format_ssn(None) is None

    def test_invalid_length(self):
        assert format_ssn("12345") == "12345"


class TestIsValidAccountNumber:
    def test_valid(self):
        assert is_valid_account_number("AB1234567890") is True

    def test_lowercase_valid(self):
        assert is_valid_account_number("ab1234567890") is True

    def test_none(self):
        assert is_valid_account_number(None) is False

    def test_invalid_format(self):
        assert is_valid_account_number("12AB345678") is False


class TestLuhnCheck:
    def test_valid_card(self):
        assert luhn_check("4532015112830366") is True

    def test_invalid_card(self):
        assert luhn_check("1234567890123456") is False

    def test_none(self):
        assert luhn_check(None) is False

    def test_empty(self):
        assert luhn_check("") is False


class TestMaskField:
    def test_ssn_mask(self):
        assert mask_field("123-45-6789", 4) == "***-**-6789"

    def test_none(self):
        assert mask_field(None, 4) is None

    def test_short_value(self):
        assert mask_field("abc", 4) == "abc"

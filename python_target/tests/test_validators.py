"""Unit tests for python_target/routines/validators.py."""

from python_target.routines.validators import (
    format_ssn,
    is_valid_account_number,
    is_valid_ssn,
    luhn_check,
    mask_field,
)


class TestIsValidSSN:
    def test_valid_ssn_with_dashes(self):
        assert is_valid_ssn("123-45-6789") is True

    def test_valid_ssn_without_dashes(self):
        assert is_valid_ssn("123456789") is True

    def test_invalid_area_000(self):
        assert is_valid_ssn("000-12-3456") is False

    def test_invalid_area_666(self):
        assert is_valid_ssn("666-12-3456") is False

    def test_invalid_area_9xx(self):
        assert is_valid_ssn("900-12-3456") is False

    def test_invalid_group_00(self):
        assert is_valid_ssn("123-00-6789") is False

    def test_invalid_serial_0000(self):
        assert is_valid_ssn("123-45-0000") is False

    def test_empty_string(self):
        assert is_valid_ssn("") is False

    def test_none(self):
        assert is_valid_ssn(None) is False


class TestFormatSSN:
    def test_formats_digits(self):
        assert format_ssn("123456789") == "123-45-6789"

    def test_already_formatted(self):
        assert format_ssn("123-45-6789") == "123-45-6789"

    def test_none_returns_none(self):
        assert format_ssn(None) is None


class TestIsValidAccountNumber:
    def test_valid(self):
        assert is_valid_account_number("AB1234567890") is True

    def test_invalid_no_alpha(self):
        assert is_valid_account_number("121234567890") is False

    def test_none(self):
        assert is_valid_account_number(None) is False


class TestLuhnCheck:
    def test_valid_number(self):
        assert luhn_check("79927398713") is True

    def test_invalid_number(self):
        assert luhn_check("79927398710") is False

    def test_empty(self):
        assert luhn_check("") is False

    def test_none(self):
        assert luhn_check(None) is False


class TestMaskField:
    def test_mask_ssn(self):
        assert mask_field("123456789", 4) == "*****6789"

    def test_none_returns_none(self):
        assert mask_field(None, 4) is None

    def test_short_value(self):
        assert mask_field("12", 4) == "12"

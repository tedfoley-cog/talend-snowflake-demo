"""Unit tests for routines/date_utils.py (converted from DateFormatUtils.java)."""
from datetime import datetime

import pytest

from python_target.routines.date_utils import (
    convert_date_format,
    format_date,
    get_fiscal_quarter,
    parse_date,
)


class TestParseDate:
    def test_valid_date(self):
        result = parse_date("2024-01-15", "yyyy-MM-dd")
        assert result == datetime(2024, 1, 15)

    def test_null_returns_none(self):
        assert parse_date(None, "yyyy-MM-dd") is None

    def test_empty_returns_none(self):
        assert parse_date("", "yyyy-MM-dd") is None

    def test_whitespace_returns_none(self):
        assert parse_date("   ", "yyyy-MM-dd") is None

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_date("not-a-date", "yyyy-MM-dd")

    def test_trims_whitespace(self):
        result = parse_date("  2024-01-15  ", "yyyy-MM-dd")
        assert result == datetime(2024, 1, 15)


class TestFormatDate:
    def test_format_date(self):
        dt = datetime(2024, 1, 15)
        assert format_date(dt, "MM/dd/yyyy") == "01/15/2024"

    def test_none_returns_empty(self):
        assert format_date(None, "yyyy-MM-dd") == ""


class TestConvertDateFormat:
    def test_converts_format(self):
        result = convert_date_format("2024-01-15", "yyyy-MM-dd", "MM/dd/yyyy")
        assert result == "01/15/2024"

    def test_null_returns_empty(self):
        assert convert_date_format(None, "yyyy-MM-dd", "MM/dd/yyyy") == ""


class TestGetFiscalQuarter:
    def test_q1_october(self):
        assert get_fiscal_quarter(datetime(2024, 10, 1)) == "Q1-FY2025"

    def test_q1_december(self):
        assert get_fiscal_quarter(datetime(2024, 12, 31)) == "Q1-FY2025"

    def test_q2_january(self):
        assert get_fiscal_quarter(datetime(2024, 1, 15)) == "Q2-FY2024"

    def test_q3_april(self):
        assert get_fiscal_quarter(datetime(2024, 4, 1)) == "Q3-FY2024"

    def test_q4_july(self):
        assert get_fiscal_quarter(datetime(2024, 7, 15)) == "Q4-FY2024"

    def test_none_returns_none(self):
        assert get_fiscal_quarter(None) is None

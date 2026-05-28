"""Unit tests for python_target/routines/date_utils.py."""
from datetime import datetime


from python_target.routines.date_utils import (
    convert_date_format,
    format_date,
    get_fiscal_quarter,
    parse_date,
)


class TestParseDate:
    def test_standard(self):
        result = parse_date("2024-01-15", "yyyy-MM-dd")
        assert result == datetime(2024, 1, 15)

    def test_empty(self):
        assert parse_date("", "yyyy-MM-dd") is None

    def test_none(self):
        assert parse_date(None, "yyyy-MM-dd") is None


class TestFormatDate:
    def test_standard(self):
        dt = datetime(2024, 1, 15)
        assert format_date(dt, "MM/dd/yyyy") == "01/15/2024"

    def test_none(self):
        assert format_date(None, "yyyy-MM-dd") == ""


class TestConvertDateFormat:
    def test_converts(self):
        result = convert_date_format("2024-01-15", "yyyy-MM-dd", "MM/dd/yyyy")
        assert result == "01/15/2024"


class TestGetFiscalQuarter:
    def test_q1_october(self):
        assert get_fiscal_quarter(datetime(2024, 10, 1)) == "Q1-FY2025"

    def test_q2_january(self):
        assert get_fiscal_quarter(datetime(2024, 1, 15)) == "Q2-FY2024"

    def test_q3_april(self):
        assert get_fiscal_quarter(datetime(2024, 4, 1)) == "Q3-FY2024"

    def test_q4_july(self):
        assert get_fiscal_quarter(datetime(2024, 7, 15)) == "Q4-FY2024"

    def test_none(self):
        assert get_fiscal_quarter(None) is None

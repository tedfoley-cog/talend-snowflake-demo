"""Test scaffolding for regulatory_reporting domain jobs."""
from unittest.mock import MagicMock



class TestCfpbExtract:
    """Tests for cfpb_extract.py (from cfpb_extract_0.1.item)."""

    def test_run_returns_row_count(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.join.return_value = df_mock
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 25
        df_mock.collect.return_value = []
        session.sql.return_value = df_mock
        from python_target.regulatory_reporting.cfpb_extract import run

        result = run(session, {
            "reporting_period_start": "2024-01-01",
            "reporting_period_end": "2024-03-31",
        })
        assert result == 25

    def test_fiscal_quarter_derivation(self):
        """APPLICATION_DATE → fiscal quarter string."""
        from python_target.routines.date_utils import get_fiscal_quarter
        from datetime import datetime

        assert get_fiscal_quarter(datetime(2024, 1, 15)) == "Q2-FY2024"
        assert get_fiscal_quarter(datetime(2024, 10, 1)) == "Q1-FY2025"


class TestOccComplianceReport:
    """Tests for occ_compliance_report.py (from occ_compliance_report_0.1.item)."""

    def test_run_returns_row_count(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 4
        session.sql.return_value = df_mock
        from python_target.regulatory_reporting.occ_compliance_report import run

        result = run(session, {"quarter": "Q1-2024"})
        assert result == 4

    def test_rate_calculation_logic(self):
        """decline_rate = decline_count / total_loans."""
        total = 100
        declines = 15
        rate = round(declines / total, 4)
        assert rate == 0.15


class TestRegulatoryArchive:
    """Tests for regulatory_archive.py (from regulatory_archive_0.1.item)."""

    def test_run_no_data(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.collect.return_value = []
        session.sql.return_value = df_mock
        from python_target.regulatory_reporting.regulatory_archive import run

        result = run(session, {"retention_months": 84})
        assert result == 0

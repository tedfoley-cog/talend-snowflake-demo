"""Unit test scaffolding for regulatory_reporting/regulatory_archive.py."""

import pandas as pd


class TestRegulatoryArchive:
    def test_run_queries_compliance_reports(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "REPORT_ID": [], "REPORT_TYPE": [], "QUARTER": [],
            "GENERATED_AT": [], "REPORT_DATA": [],
        })
        sample_config["archive_dir"] = "/tmp/"
        from python_target.regulatory_reporting.regulatory_archive import run

        run(mock_session, sample_config)
        query = mock_session.sql.call_args[0][0]
        assert "COMPLIANCE_REPORTS" in query

    def test_run_applies_retention_filter(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "REPORT_ID": [], "REPORT_TYPE": [], "QUARTER": [],
            "GENERATED_AT": [], "REPORT_DATA": [],
        })
        sample_config["archive_dir"] = "/tmp/"
        from python_target.regulatory_reporting.regulatory_archive import run

        run(mock_session, sample_config)
        query = mock_session.sql.call_args[0][0]
        assert "DATEADD" in query
        assert "84" in query

    def test_run_writes_pipe_delimited_csv(self, mock_session, sample_config, tmp_path):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "REPORT_ID": ["R1"], "REPORT_TYPE": ["OCC"],
            "QUARTER": ["Q1-2024"], "GENERATED_AT": ["2024-03-31"],
            "REPORT_DATA": ["{}"],
        })
        sample_config["archive_dir"] = str(tmp_path) + "/"
        from python_target.regulatory_reporting.regulatory_archive import run

        run(mock_session, sample_config)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        content = files[0].read_text()
        assert "|" in content

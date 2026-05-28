"""Unit test scaffolding for regulatory_reporting/cfpb_extract.py."""

import pandas as pd


class TestCfpbExtract:
    def test_run_queries_three_sources(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "APPLICATION_ID": [], "LOAN_TYPE": [], "REQUESTED_AMOUNT": [],
            "APPLICATION_DATE_FMT": [], "ACTION_TAKEN": [], "STATE_CODE": [],
            "CENSUS_TRACT": [], "INCOME_BRACKET": [], "REPORT_PERIOD": [],
        })
        sample_config["output_dir"] = "/tmp/"
        from python_target.regulatory_reporting.cfpb_extract import run

        run(mock_session, sample_config)
        assert mock_session.sql.call_count >= 3

    def test_run_joins_apps_demographics_adverse(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "APPLICATION_ID": [], "LOAN_TYPE": [], "REQUESTED_AMOUNT": [],
            "APPLICATION_DATE_FMT": [], "ACTION_TAKEN": [], "STATE_CODE": [],
            "CENSUS_TRACT": [], "INCOME_BRACKET": [], "REPORT_PERIOD": [],
        })
        sample_config["output_dir"] = "/tmp/"
        from python_target.regulatory_reporting.cfpb_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        assert df.join.call_count >= 2

    def test_run_computes_action_taken(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "APPLICATION_ID": [], "LOAN_TYPE": [], "REQUESTED_AMOUNT": [],
            "APPLICATION_DATE_FMT": [], "ACTION_TAKEN": [], "STATE_CODE": [],
            "CENSUS_TRACT": [], "INCOME_BRACKET": [], "REPORT_PERIOD": [],
        })
        sample_config["output_dir"] = "/tmp/"
        from python_target.regulatory_reporting.cfpb_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "ACTION_TAKEN" in col_names
        assert "INCOME_BRACKET" in col_names

    def test_run_writes_pipe_delimited_csv(self, mock_session, sample_config, tmp_path):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "APPLICATION_ID": ["A1"], "LOAN_TYPE": ["AUTO"],
            "REQUESTED_AMOUNT": [25000.0],
            "APPLICATION_DATE_FMT": ["01/15/2024"],
            "ACTION_TAKEN": ["AUTO_APPROVE"], "STATE_CODE": ["CA"],
            "CENSUS_TRACT": ["900"], "INCOME_BRACKET": ["HIGH"],
            "REPORT_PERIOD": ["2024-01-01 to 2024-03-31"],
        })
        sample_config["output_dir"] = str(tmp_path) + "/"
        from python_target.regulatory_reporting.cfpb_extract import run

        run(mock_session, sample_config)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        content = files[0].read_text()
        assert "|" in content

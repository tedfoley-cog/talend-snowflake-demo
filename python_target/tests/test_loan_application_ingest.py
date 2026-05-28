"""Unit test scaffolding for loan_processing/loan_application_ingest.py."""

import pytest


class TestLoanApplicationIngest:
    @pytest.fixture()
    def csv_file(self, tmp_path):
        csv = tmp_path / "daily_loan_applications.csv"
        csv.write_text(
            "APPLICATION_ID,CUSTOMER_ID,LOAN_TYPE,REQUESTED_AMOUNT,"
            "TERM_MONTHS,INTEREST_RATE,COLLATERAL_TYPE,COLLATERAL_VALUE,"
            "ANNUAL_INCOME,CREDIT_SCORE,APPLICATION_DATE,STATUS\n"
            "APP001,C001,auto,25000,60,5.5,VEHICLE,30000,75000,720,2024-01-15,PENDING\n"
        )
        return str(tmp_path) + "/"

    def test_run_reads_csv_and_writes(self, mock_session, sample_config, csv_file):
        from python_target.loan_processing.loan_application_ingest import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        mock_session.create_dataframe.assert_called_once()

    def test_run_computes_dti_ratio(self, mock_session, sample_config, csv_file):
        from python_target.loan_processing.loan_application_ingest import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        rows = mock_session.create_dataframe.call_args[0][0]
        assert "DTI_RATIO" in rows[0]
        assert rows[0]["DTI_RATIO"] > 0

    def test_run_computes_ltv_ratio(self, mock_session, sample_config, csv_file):
        from python_target.loan_processing.loan_application_ingest import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        rows = mock_session.create_dataframe.call_args[0][0]
        assert "LTV_RATIO" in rows[0]
        assert rows[0]["LTV_RATIO"] is not None

    def test_run_formats_loan_type_uppercase(self, mock_session, sample_config, csv_file):
        from python_target.loan_processing.loan_application_ingest import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        rows = mock_session.create_dataframe.call_args[0][0]
        assert rows[0]["LOAN_TYPE"] == "AUTO"

    def test_run_writes_to_stg_loan_application(self, mock_session, sample_config, csv_file):
        from python_target.loan_processing.loan_application_ingest import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        df = mock_session.create_dataframe.return_value
        df.write.mode.assert_called_with("append")
        save = df.write.mode.return_value.save_as_table
        assert "STG_LOAN_APPLICATION" in save.call_args[0][0]

"""Unit test scaffolding for payment_reconciliation/payment_discrepancy.py."""

import pandas as pd


class TestPaymentDiscrepancy:
    def test_run_queries_unmatched_payments(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "PAYMENT_ID": [], "LOAN_ID": [], "CUSTOMER_ID": [],
            "PAYMENT_AMOUNT": [], "AMOUNT_DUE": [], "VARIANCE": [],
            "MATCH_STATUS": [], "RECONCILED_AT": [],
        })
        sample_config["output_dir"] = "/tmp/"
        from python_target.payment_reconciliation.payment_discrepancy import run

        run(mock_session, sample_config)
        query = mock_session.sql.call_args[0][0]
        assert "PAYMENT_RECONCILIATION" in query
        assert "MATCHED" in query

    def test_run_formats_currency_columns(self, mock_session, sample_config):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "PAYMENT_ID": ["P1"], "LOAN_ID": ["L1"], "CUSTOMER_ID": ["C1"],
            "PAYMENT_AMOUNT": [100.50], "AMOUNT_DUE": [99.00],
            "VARIANCE": [1.50], "MATCH_STATUS": ["OVERPAYMENT"],
            "RECONCILED_AT": ["2024-01-15"],
        })
        sample_config["output_dir"] = "/tmp/"
        from python_target.payment_reconciliation.payment_discrepancy import run

        run(mock_session, sample_config)

    def test_run_writes_csv_output(self, mock_session, sample_config, tmp_path):
        mock_session.sql.return_value.to_pandas.return_value = pd.DataFrame({
            "PAYMENT_ID": ["P1"], "LOAN_ID": ["L1"], "CUSTOMER_ID": ["C1"],
            "PAYMENT_AMOUNT": [100.50], "AMOUNT_DUE": [99.00],
            "VARIANCE": [1.50], "MATCH_STATUS": ["OVERPAYMENT"],
            "RECONCILED_AT": ["2024-01-15"],
        })
        sample_config["output_dir"] = str(tmp_path) + "/"
        from python_target.payment_reconciliation.payment_discrepancy import run

        run(mock_session, sample_config)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name.startswith("discrepancy_report_")

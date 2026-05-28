"""Unit test scaffolding for regulatory_reporting/occ_compliance_report.py."""



class TestOccComplianceReport:
    def test_run_queries_portfolio_view(self, mock_session, sample_config):
        from python_target.regulatory_reporting.occ_compliance_report import run

        run(mock_session, sample_config)
        query = mock_session.sql.call_args[0][0]
        assert "LOAN_PORTFOLIO_VIEW" in query

    def test_run_computes_rate_columns(self, mock_session, sample_config):
        from python_target.regulatory_reporting.occ_compliance_report import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "DECLINE_RATE" in col_names
        assert "DELINQUENCY_RATE_30" in col_names
        assert "DELINQUENCY_RATE_60" in col_names
        assert "DELINQUENCY_RATE_90" in col_names
        assert "QUARTER" in col_names

    def test_run_writes_to_occ_table(self, mock_session, sample_config):
        from python_target.regulatory_reporting.occ_compliance_report import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called_with("append")
        save = df.write.mode.return_value.save_as_table
        assert "OCC_COMPLIANCE_REPORT" in save.call_args[0][0]

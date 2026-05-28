"""Unit test scaffolding for loan_processing/loan_risk_scoring.py."""



class TestLoanRiskScoring:
    def test_run_queries_pending_applications(self, mock_session, sample_config):
        from python_target.loan_processing.loan_risk_scoring import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("PENDING_REVIEW" in q for q in queries)

    def test_run_computes_risk_factors(self, mock_session, sample_config):
        from python_target.loan_processing.loan_risk_scoring import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "DTI_RATIO" in col_names
        assert "CREDIT_FACTOR" in col_names
        assert "EMPLOYMENT_FACTOR" in col_names
        assert "DTI_FACTOR" in col_names
        assert "RISK_SCORE" in col_names

    def test_run_classifies_risk_tier(self, mock_session, sample_config):
        from python_target.loan_processing.loan_risk_scoring import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "RISK_TIER" in col_names
        assert "DECISION" in col_names

    def test_run_writes_to_loan_risk_scores(self, mock_session, sample_config):
        from python_target.loan_processing.loan_risk_scoring import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called()

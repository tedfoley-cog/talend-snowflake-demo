"""Unit test scaffolding for loan_processing/loan_status_update.py."""



class TestLoanStatusUpdate:
    def test_run_queries_recent_scores(self, mock_session, sample_config):
        from python_target.loan_processing.loan_status_update import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("LOAN_RISK_SCORES" in q for q in queries)

    def test_run_executes_merge_update(self, mock_session, sample_config):
        from python_target.loan_processing.loan_status_update import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("MERGE INTO LOAN_APPLICATION" in q for q in queries)

    def test_run_logs_count(self, mock_session, sample_config):
        from python_target.loan_processing.loan_status_update import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.count.assert_called()

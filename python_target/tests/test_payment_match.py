"""Unit test scaffolding for payment_reconciliation/payment_match.py."""



class TestPaymentMatch:
    def test_run_queries_payments_and_balances(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_match import run

        run(mock_session, sample_config)
        assert mock_session.sql.call_count >= 2
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("INCOMING_PAYMENTS" in q for q in queries)
        assert any("LOAN_BALANCE" in q for q in queries)

    def test_run_joins_on_loan_id(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_match import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.join.assert_called_once()

    def test_run_computes_variance(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_match import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "VARIANCE" in col_names

    def test_run_classifies_match_status(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_match import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "MATCH_STATUS" in col_names

    def test_run_writes_to_payment_reconciliation(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_match import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called_with("append")

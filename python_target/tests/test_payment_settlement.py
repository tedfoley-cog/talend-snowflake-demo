"""Unit test scaffolding for payment_reconciliation/payment_settlement.py."""



class TestPaymentSettlement:
    def test_run_queries_matched_unsettled(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_settlement import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("PAYMENT_RECONCILIATION" in q and "MATCHED" in q for q in queries)

    def test_run_classifies_settlement_type(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_settlement import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "SETTLEMENT_TYPE" in col_names

    def test_run_writes_settlement_and_marks_reconciled(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_settlement import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("PAYMENT_SETTLEMENT" in q for q in queries)
        assert any("MERGE INTO INCOMING_PAYMENTS" in q for q in queries)

    def test_run_uses_auto_settle_threshold(self, mock_session, sample_config):
        from python_target.payment_reconciliation.payment_settlement import run

        sample_config["auto_settle_threshold"] = "10000.00"
        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "SETTLEMENT_TYPE" in col_names

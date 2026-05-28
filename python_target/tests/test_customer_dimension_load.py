"""Unit test scaffolding for customer_accounts/customer_dimension_load.py."""



class TestCustomerDimensionLoad:
    def test_run_detects_changed_customers(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_dimension_load import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("STG_CUSTOMER" in q and "DIM_CUSTOMER" in q for q in queries)

    def test_run_expires_existing_scd_records(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_dimension_load import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("MERGE INTO" in q and "IS_CURRENT" in q for q in queries)

    def test_run_inserts_new_dimension_records(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_dimension_load import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called_with("append")

    def test_run_sets_scd2_fields(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_dimension_load import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        select_called = df.select.called
        assert select_called

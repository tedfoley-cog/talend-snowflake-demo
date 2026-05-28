"""Unit test scaffolding for customer_accounts/customer_extract.py."""



class TestCustomerExtract:
    def test_run_executes_sql_query(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_extract import run

        run(mock_session, sample_config)
        mock_session.sql.assert_called_once()
        query = mock_session.sql.call_args[0][0]
        assert "CUSTOMER_MASTER" in query

    def test_run_writes_to_stg_customer(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called_with("append")
        save_call = df.write.mode.return_value.save_as_table
        save_call.assert_called_once()
        assert "STG_CUSTOMER" in save_call.call_args[0][0]

    def test_run_applies_full_name_concat(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        with_column_calls = [c[0][0] for c in df.with_column.call_args_list]
        assert "FULL_NAME" in with_column_calls

    def test_run_masks_ssn(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        with_column_calls = [c[0][0] for c in df.with_column.call_args_list]
        assert "SSN_MASKED" in with_column_calls

    def test_run_adds_etl_timestamp(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_extract import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        with_column_calls = [c[0][0] for c in df.with_column.call_args_list]
        assert "ETL_LOAD_TS" in with_column_calls

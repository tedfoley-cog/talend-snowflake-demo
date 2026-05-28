"""Unit test scaffolding for customer_accounts/customer_validation.py."""



class TestCustomerValidation:
    def test_run_queries_active_customers(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_validation import run

        run(mock_session, sample_config)
        query = mock_session.sql.call_args[0][0]
        assert "CUSTOMER_MASTER" in query
        assert "ACTIVE" in query

    def test_run_adds_validation_columns(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_validation import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "SSN_VALID" in col_names
        assert "EMAIL_VALID" in col_names
        assert "PHONE_VALID" in col_names
        assert "ZIP_VALID" in col_names
        assert "ALL_VALID" in col_names

    def test_run_writes_valid_records(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_validation import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.filter.assert_called()

    def test_run_splits_valid_and_invalid(self, mock_session, sample_config):
        from python_target.customer_accounts.customer_validation import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        assert df.filter.call_count >= 2

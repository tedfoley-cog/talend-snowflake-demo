"""Unit test scaffolding for data_quality/dedup_customer.py."""



class TestDedupCustomer:
    def test_run_queries_potential_duplicates(self, mock_session, sample_config):
        from python_target.data_quality.dedup_customer import run

        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("STG_CUSTOMER" in q and "JAROWINKLER_SIMILARITY" in q for q in queries)

    def test_run_classifies_match_type(self, mock_session, sample_config):
        from python_target.data_quality.dedup_customer import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        col_names = [c[0][0] for c in df.with_column.call_args_list]
        assert "SSN_MATCH" in col_names
        assert "EMAIL_MATCH" in col_names
        assert "NAME_MATCH" in col_names
        assert "MATCH_TYPE" in col_names
        assert "CONFIDENCE" in col_names

    def test_run_writes_dedup_results(self, mock_session, sample_config):
        from python_target.data_quality.dedup_customer import run

        run(mock_session, sample_config)
        df = mock_session.sql.return_value
        df.write.mode.assert_called_with("append")
        save = df.write.mode.return_value.save_as_table
        assert "CUSTOMER_DEDUP_RESULTS" in save.call_args[0][0]

    def test_run_uses_similarity_threshold(self, mock_session, sample_config):
        from python_target.data_quality.dedup_customer import run

        sample_config["similarity_threshold"] = "0.90"
        run(mock_session, sample_config)
        queries = [c[0][0] for c in mock_session.sql.call_args_list]
        assert any("90" in q for q in queries)

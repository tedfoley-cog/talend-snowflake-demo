"""Shared pytest fixtures for Snowpark job tests."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def mock_session():
    """Return a mock Snowpark Session with common method chains."""
    session = MagicMock(name="Session")
    df_mock = MagicMock(name="DataFrame")
    df_mock.count.return_value = 5
    df_mock.collect.return_value = []
    df_mock.to_pandas.return_value.__len__ = lambda self: 0

    df_mock.with_column.return_value = df_mock
    df_mock.select.return_value = df_mock
    df_mock.filter.return_value = df_mock
    df_mock.join.return_value = df_mock
    df_mock.write.mode.return_value.save_as_table.return_value = None

    session.sql.return_value = df_mock
    session.table.return_value = df_mock
    session.create_dataframe.return_value = df_mock

    return session


@pytest.fixture()
def sample_config():
    """Return a default config dict for tests."""
    return {
        "batch_date": "2024-01-01",
        "tgt_schema": "RAW",
        "src_schema": "RAW",
        "src_db_host": "localhost",
        "recon_date": "2024-01-15",
        "match_tolerance": "0.01",
        "auto_settle_threshold": "5000.00",
        "quarter": "Q1-2024",
        "reporting_period_start": "2024-01-01",
        "reporting_period_end": "2024-03-31",
        "output_dir": "/tmp/test_output/",
        "archive_dir": "/tmp/test_archive/",
        "retention_months": "84",
        "input_dir": "/tmp/test_input/",
        "report_date": "2024-01-15",
        "similarity_threshold": "0.85",
        "effective_date": "2024-01-01",
        "risk_model_version": "v3.2",
    }

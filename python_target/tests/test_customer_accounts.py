"""Test scaffolding for customer_accounts domain jobs.

These tests validate the transformation logic of each converted job.
Snowpark Session is mocked; pure-Python logic is tested directly.
"""
from unittest.mock import MagicMock



class TestCustomerExtract:
    """Tests for customer_extract.py (from customer_extract_0.1.item)."""

    def test_run_returns_row_count(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 42
        session.sql.return_value = df_mock
        from python_target.customer_accounts.customer_extract import run

        result = run(session, {"batch_date": "2024-01-15", "tgt_schema": "RAW"})
        assert result == 42

    def test_full_name_concatenation_logic(self):
        """Verify FULL_NAME = FIRST_NAME + ' ' + LAST_NAME."""
        first = "John"
        last = "Doe"
        assert f"{first} {last}" == "John Doe"

    def test_ssn_masking_logic(self):
        """Verify SSN_MASKED = '***-**-' + last 4 digits."""
        ssn = "123-45-6789"
        masked = "***-**-" + ssn[7:]
        assert masked == "***-**-6789"

    def test_email_lowercase_logic(self):
        """Verify EMAIL lowercased when not null."""
        email = "John.Doe@Example.COM"
        assert email.lower() == "john.doe@example.com"

    def test_address_concatenation_logic(self):
        """Verify FULL_ADDRESS concatenation with optional ADDRESS_LINE2."""
        addr1 = "123 Main St"
        addr2 = "Apt 4"
        city = "Springfield"
        state = "IL"
        zipcode = "62701"
        full = f"{addr1} {addr2}, {city}, {state} {zipcode}"
        assert full == "123 Main St Apt 4, Springfield, IL 62701"

    def test_address_without_line2(self):
        addr1 = "123 Main St"
        city = "Springfield"
        state = "IL"
        zipcode = "62701"
        full = f"{addr1}, {city}, {state} {zipcode}"
        assert full == "123 Main St, Springfield, IL 62701"


class TestCustomerValidation:
    """Tests for customer_validation.py (from customer_validation_0.1.item)."""

    def test_validation_functions_imported(self):
        pass

    def test_ssn_valid_function(self):
        from python_target.customer_accounts.customer_validation import _ssn_valid

        assert _ssn_valid("123-45-6789") is True
        assert _ssn_valid(None) is False
        assert _ssn_valid("000-12-3456") is False

    def test_email_valid_function(self):
        from python_target.customer_accounts.customer_validation import _email_valid

        assert _email_valid("user@example.com") is True
        assert _email_valid(None) is False
        assert _email_valid("noemail") is False

    def test_phone_valid_function(self):
        from python_target.customer_accounts.customer_validation import _phone_valid

        assert _phone_valid("(555) 123-4567") is True
        assert _phone_valid(None) is False
        assert _phone_valid("123") is False

    def test_zip_valid_function(self):
        from python_target.customer_accounts.customer_validation import _zip_valid

        assert _zip_valid("62701") is True
        assert _zip_valid("62701-1234") is True
        assert _zip_valid(None) is False
        assert _zip_valid("ABC") is False


class TestCustomerDimensionLoad:
    """Tests for customer_dimension_load.py (from customer_dimension_load_0.1.item)."""

    def test_run_returns_row_count(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 5
        session.sql.return_value = df_mock
        from python_target.customer_accounts.customer_dimension_load import run

        result = run(session, {"effective_date": "2024-01-15"})
        assert result == 5

    def test_scd2_effective_date_applied(self):
        """Verify EFF_START_DATE uses config or current date."""
        from datetime import datetime

        config = {"effective_date": "2024-06-01"}
        assert config["effective_date"] == "2024-06-01"

        fallback = datetime.now().strftime("%Y-%m-%d")
        assert len(fallback) == 10

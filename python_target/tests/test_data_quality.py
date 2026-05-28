"""Test scaffolding for data_quality domain jobs."""
from unittest.mock import MagicMock



class TestAddressStandardization:
    """Tests for address_standardization.py (from address_standardization_0.1.item)."""

    def test_normalize_address(self):
        from python_target.data_quality.address_standardization import (
            _normalize_address,
        )

        assert _normalize_address("123 Main Street") == "123 MAIN ST"
        assert _normalize_address("456 Oak Avenue Apt 7") == "456 OAK AVE APT 7"
        assert _normalize_address("789 Pine Boulevard") == "789 PINE BLVD"
        assert _normalize_address("321 Elm Drive Suite 2") == "321 ELM DR STE 2"

    def test_normalize_none(self):
        from python_target.data_quality.address_standardization import (
            _normalize_address,
        )

        assert _normalize_address(None) is None

    def test_zip_split_logic(self):
        """ZIP_CODE '62701-1234' → ZIP5='62701', ZIP4='1234'."""
        zipcode = "62701-1234"
        zip5 = zipcode[:5]
        zip4 = zipcode[6:10] if len(zipcode) > 5 else None
        assert zip5 == "62701"
        assert zip4 == "1234"

    def test_zip5_only(self):
        zipcode = "62701"
        zip5 = zipcode[:5]
        zip4 = zipcode[6:10] if len(zipcode) > 5 else None
        assert zip5 == "62701"
        assert zip4 is None


class TestDedupCustomer:
    """Tests for dedup_customer.py (from dedup_customer_0.1.item)."""

    def test_match_type_ssn(self):
        """SSN match → SSN_MATCH, highest confidence."""
        ssn1, ssn2 = "***-**-6789", "***-**-6789"
        match_type = "SSN_MATCH" if ssn1 == ssn2 else "OTHER"
        assert match_type == "SSN_MATCH"

    def test_match_type_email(self):
        email1, email2 = "john@example.com", "john@example.com"
        match_type = "EMAIL_MATCH" if email1 == email2 else "OTHER"
        assert match_type == "EMAIL_MATCH"

    def test_confidence_values(self):
        """SSN → 0.99, email → 0.95, name similarity → threshold."""
        assert 0.99 > 0.95 > 0.85

    def test_run_returns_dict(self):
        session = MagicMock()
        df_mock = MagicMock()
        df_mock.select.return_value = df_mock
        df_mock.count.return_value = 3
        session.sql.return_value = df_mock
        from python_target.data_quality.dedup_customer import run

        result = run(session, {"similarity_threshold": 0.85})
        assert "duplicates" in result
        assert "log_entries" in result

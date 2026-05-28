"""Unit test scaffolding for data_quality/address_standardization.py."""
import pytest

from python_target.data_quality.address_standardization import normalize_address


class TestNormalizeAddress:
    def test_abbreviates_street(self):
        assert normalize_address("123 MAIN STREET") == "123 MAIN ST"

    def test_abbreviates_avenue(self):
        assert normalize_address("456 OAK AVENUE") == "456 OAK AVE"

    def test_abbreviates_boulevard(self):
        assert normalize_address("789 SUNSET BOULEVARD") == "789 SUNSET BLVD"

    def test_abbreviates_drive(self):
        assert normalize_address("100 PARK DRIVE") == "100 PARK DR"

    def test_abbreviates_apartment(self):
        assert normalize_address("200 APARTMENT 3B") == "200 APT 3B"

    def test_abbreviates_suite(self):
        assert normalize_address("300 SUITE 100") == "300 STE 100"

    def test_uppercases(self):
        assert normalize_address("123 main street") == "123 MAIN ST"

    def test_none_returns_none(self):
        assert normalize_address(None) is None


class TestAddressStandardizationJob:
    @pytest.fixture()
    def csv_file(self, tmp_path):
        csv = tmp_path / "address_corrections.csv"
        csv.write_text(
            "CUSTOMER_ID,ADDRESS_LINE1,ADDRESS_LINE2,CITY,STATE_CODE,ZIP_CODE\n"
            "C001,123 Main Street,,Springfield,IL,62701-1234\n"
        )
        return str(tmp_path) + "/"

    def test_run_reads_csv(self, mock_session, sample_config, csv_file):
        from python_target.data_quality.address_standardization import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        mock_session.create_dataframe.assert_called_once()

    def test_run_splits_zip(self, mock_session, sample_config, csv_file):
        from python_target.data_quality.address_standardization import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        rows = mock_session.create_dataframe.call_args[0][0]
        assert rows[0]["ZIP5"] == "62701"
        assert rows[0]["ZIP4"] == "1234"

    def test_run_writes_to_stg_table(self, mock_session, sample_config, csv_file):
        from python_target.data_quality.address_standardization import run

        sample_config["input_dir"] = csv_file
        run(mock_session, sample_config)
        df = mock_session.create_dataframe.return_value
        df.write.mode.assert_called()

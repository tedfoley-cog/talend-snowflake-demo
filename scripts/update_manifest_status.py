"""Update migration manifest to reflect conversion completion status."""
import json
import sys

JOB_FILES = {
    "customer_extract": (
        "python_target/customer_accounts/customer_extract.py",
        "python_target/tests/test_customer_accounts.py",
    ),
    "customer_validation": (
        "python_target/customer_accounts/customer_validation.py",
        "python_target/tests/test_customer_accounts.py",
    ),
    "customer_dimension_load": (
        "python_target/customer_accounts/customer_dimension_load.py",
        "python_target/tests/test_customer_accounts.py",
    ),
    "loan_application_ingest": (
        "python_target/loan_processing/loan_application_ingest.py",
        "python_target/tests/test_loan_processing.py",
    ),
    "loan_risk_scoring": (
        "python_target/loan_processing/loan_risk_scoring.py",
        "python_target/tests/test_loan_processing.py",
    ),
    "loan_status_update": (
        "python_target/loan_processing/loan_status_update.py",
        "python_target/tests/test_loan_processing.py",
    ),
    "payment_match": (
        "python_target/payment_reconciliation/payment_match.py",
        "python_target/tests/test_payment_reconciliation.py",
    ),
    "payment_discrepancy": (
        "python_target/payment_reconciliation/payment_discrepancy.py",
        "python_target/tests/test_payment_reconciliation.py",
    ),
    "payment_settlement": (
        "python_target/payment_reconciliation/payment_settlement.py",
        "python_target/tests/test_payment_reconciliation.py",
    ),
    "cfpb_extract": (
        "python_target/regulatory_reporting/cfpb_extract.py",
        "python_target/tests/test_regulatory_reporting.py",
    ),
    "occ_compliance_report": (
        "python_target/regulatory_reporting/occ_compliance_report.py",
        "python_target/tests/test_regulatory_reporting.py",
    ),
    "regulatory_archive": (
        "python_target/regulatory_reporting/regulatory_archive.py",
        "python_target/tests/test_regulatory_reporting.py",
    ),
    "address_standardization": (
        "python_target/data_quality/address_standardization.py",
        "python_target/tests/test_data_quality.py",
    ),
    "dedup_customer": (
        "python_target/data_quality/dedup_customer.py",
        "python_target/tests/test_data_quality.py",
    ),
}


def main():
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else "analysis_output/migration_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    for job in manifest["jobs"]:
        name = job["job_name"]
        if name in JOB_FILES:
            job["conversion_status"] = "COMPLETE"
            job["converted_file"] = JOB_FILES[name][0]
            job["test_file"] = JOB_FILES[name][1]

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    done = sum(1 for j in manifest["jobs"] if j["conversion_status"] == "COMPLETE")
    print(f"Updated {done}/{len(manifest['jobs'])} jobs to COMPLETE")


if __name__ == "__main__":
    main()

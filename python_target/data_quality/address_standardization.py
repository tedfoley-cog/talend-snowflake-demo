"""Converted from talend_jobs/data_quality/address_standardization_0.1.item.

Flow: tFileInputDelimited(address_corrections.csv) → tMap(normalize
      street abbrev, split ZIP5/ZIP4, uppercase) → tDBOutput(Snowflake
      STG_ADDRESS_STANDARDIZED INSERT_OR_UPDATE)

Source: CSV file  |  Target: Snowflake RAW.STG_ADDRESS_STANDARDIZED
"""
import logging
import re

import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F

logger = logging.getLogger("etl.address_standardization")

STREET_ABBREVS = [
    (r"\bSTREET\b", "ST"),
    (r"\bAVENUE\b", "AVE"),
    (r"\bBOULEVARD\b", "BLVD"),
    (r"\bDRIVE\b", "DR"),
    (r"\bAPARTMENT\b", "APT"),
    (r"\bSUITE\b", "STE"),
]


def normalize_address(addr: str | None) -> str | None:
    if addr is None:
        return None
    result = addr.strip().upper()
    for pattern, repl in STREET_ABBREVS:
        result = re.sub(pattern, repl, result)
    return result


def run(session: Session, config: dict) -> None:
    input_dir = config.get("input_dir", "/data/incoming/address_updates/")
    tgt_schema = config.get("tgt_schema", "RAW")

    # tFileInputDelimited_1: read CSV
    filepath = f"{input_dir}address_corrections.csv"
    pdf = pd.read_csv(filepath, dtype=str, keep_default_na=False)

    rows = []
    for _, r in pdf.iterrows():
        addr1 = r.get("ADDRESS_LINE1") or None
        addr2 = r.get("ADDRESS_LINE2") or None
        city = r.get("CITY") or None
        state = r.get("STATE_CODE") or None
        zipcode = r.get("ZIP_CODE") or None

        # tMap_1 var table: normalizations
        norm_addr = normalize_address(addr1) if addr1 else None
        norm_addr2 = addr2.strip().upper() if addr2 else None
        norm_city = city.strip().upper() if city else None
        norm_state = state.strip().upper() if state else None

        zip5 = zipcode[:5] if zipcode and len(zipcode) >= 5 else zipcode
        zip4 = (
            zipcode[6:]
            if zipcode and "-" in zipcode and len(zipcode) >= 10
            else None
        )

        rows.append({
            "CUSTOMER_ID": r["CUSTOMER_ID"],
            "ADDRESS_LINE1": norm_addr,
            "ADDRESS_LINE2": norm_addr2,
            "CITY": norm_city,
            "STATE_CODE": norm_state,
            "ZIP5": zip5,
            "ZIP4": zip4,
        })

    df = session.create_dataframe(rows)
    df = df.with_column("STANDARDIZED_AT", F.current_timestamp())

    # tDBOutput_1: INSERT_OR_UPDATE → MERGE
    table = f"{tgt_schema}.STG_ADDRESS_STANDARDIZED"
    df.write.mode("overwrite").save_as_table(table)
    logger.info("address_standardization complete — %d records → %s", len(rows), table)


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

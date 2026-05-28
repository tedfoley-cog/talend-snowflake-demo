"""Converted from: talend_jobs/data_quality/address_standardization_0.1.item

Reads address correction CSV, standardizes street abbreviations
(STREET→ST, AVENUE→AVE, etc.), splits ZIP into ZIP5/ZIP4,
and loads to STG_ADDRESS_STANDARDIZED.

Components: tFileInputDelimited → tMap → tDBOutput(Snowflake)
Routines:   StringHandling
"""
import logging
import re

import pandas as pd
from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import StringType

logger = logging.getLogger("etl")

ABBREVIATIONS = {
    r"\bSTREET\b": "ST",
    r"\bAVENUE\b": "AVE",
    r"\bBOULEVARD\b": "BLVD",
    r"\bDRIVE\b": "DR",
    r"\bAPARTMENT\b": "APT",
    r"\bSUITE\b": "STE",
}


def _normalize_address(addr: str | None) -> str | None:
    if addr is None:
        return None
    result = addr.strip().upper()
    for pattern, replacement in ABBREVIATIONS.items():
        result = re.sub(pattern, replacement, result)
    return result


def run(session: Session, config: dict) -> int:
    input_dir = config.get("input_dir", "/data/incoming/address_updates/")
    filepath = f"{input_dir}address_corrections.csv"

    df_pd = pd.read_csv(filepath, dtype=str)

    normalize_udf = session.udf.register(
        _normalize_address,
        return_type=StringType(),
        input_types=[StringType()],
        name="normalize_address_udf",
        is_permanent=False,
        replace=True,
    )

    df = session.create_dataframe(df_pd.to_dict("records"))

    df_out = df.select(
        F.col("CUSTOMER_ID"),
        normalize_udf(F.col("ADDRESS_LINE1")).alias("ADDRESS_LINE1"),
        F.col("ADDRESS_LINE2"),
        F.when(F.col("CITY").is_not_null(), F.upper(F.trim(F.col("CITY"))))
        .otherwise(F.lit(None))
        .alias("CITY"),
        F.when(F.col("STATE_CODE").is_not_null(), F.upper(F.trim(F.col("STATE_CODE"))))
        .otherwise(F.lit(None))
        .alias("STATE_CODE"),
        F.substring(F.col("ZIP_CODE"), 1, 5).alias("ZIP5"),
        F.when(
            F.length(F.col("ZIP_CODE")) > F.lit(5),
            F.substring(F.col("ZIP_CODE"), 7, 4),
        )
        .otherwise(F.lit(None))
        .alias("ZIP4"),
        F.current_timestamp().alias("STANDARDIZED_AT"),
    )

    row_count = df_out.count()
    df_out.write.mode("append").save_as_table(
        f"{config.get('tgt_schema', 'RAW')}.STG_ADDRESS_STANDARDIZED"
    )
    logger.info("address_standardization: standardized %d addresses", row_count)
    return row_count

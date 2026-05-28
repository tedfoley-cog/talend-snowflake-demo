"""Converted from: talend_jobs/regulatory_reporting/regulatory_archive_0.1.item

Archives compliance reports within retention period to a
pipe-delimited CSV file.

Components: tDBInput(Snowflake) → tFileOutputDelimited
Routines:   DateFormatUtils
"""
import logging
from datetime import datetime

from snowflake.snowpark import Session

logger = logging.getLogger("etl")


def run(session: Session, config: dict) -> int:
    retention_months = config.get("retention_months", 84)
    archive_dir = config.get("archive_dir", "/data/archive/regulatory/")

    df = session.sql(f"""
        SELECT REPORT_ID, REPORT_TYPE, QUARTER, GENERATED_AT, REPORT_DATA
        FROM COMPLIANCE_REPORTS
        WHERE GENERATED_AT >= DATEADD(month, -{retention_months}, CURRENT_DATE())
        ORDER BY GENERATED_AT DESC
    """)

    rows = df.collect()
    if rows:
        import pandas as pd

        df_pd = pd.DataFrame([r.as_dict() for r in rows])
        today = datetime.now().strftime("%Y%m%d")
        output_path = f"{archive_dir}regulatory_archive_{today}.csv"
        df_pd.to_csv(output_path, sep="|", header=True, index=False, encoding="utf-8")
        logger.info("regulatory_archive: archived %d reports to %s", len(rows), output_path)
    else:
        logger.info("regulatory_archive: no reports within retention window")

    return len(rows)

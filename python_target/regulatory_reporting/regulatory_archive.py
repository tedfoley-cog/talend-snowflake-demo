"""Converted from talend_jobs/regulatory_reporting/regulatory_archive_0.1.item.

Flow: tDBInput(Snowflake COMPLIANCE_REPORTS with retention filter)
      → tFileOutputDelimited(pipe-delimited archive file)

Source: Snowflake  |  Target: CSV archive file
Custom routines: DateFormatUtils
"""
import logging
from datetime import datetime

from snowflake.snowpark import Session

logger = logging.getLogger("etl.regulatory_archive")


def run(session: Session, config: dict) -> None:
    archive_dir = config.get("archive_dir", "/data/archive/regulatory/")
    retention_months = int(config.get("retention_months", 84))

    # tDBInput_1: compliance reports within retention window
    df = session.sql(f"""
        SELECT REPORT_ID, REPORT_TYPE, QUARTER, GENERATED_AT, REPORT_DATA
        FROM COMPLIANCE_REPORTS
        WHERE GENERATED_AT >= DATEADD(month, -{retention_months}, CURRENT_DATE())
        ORDER BY GENERATED_AT DESC
    """)

    pdf = df.to_pandas()

    # tFileOutputDelimited_1: pipe-delimited archive
    today = datetime.now().strftime("%Y%m%d")
    out_path = f"{archive_dir}regulatory_archive_{today}.csv"
    pdf.to_csv(out_path, sep="|", index=False, header=True, encoding="utf-8")
    logger.info("regulatory_archive complete — %s (%d reports)", out_path, len(pdf))


if __name__ == "__main__":
    raise SystemExit("Run via orchestrator or import run(session, config)")

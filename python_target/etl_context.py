"""ETL job lifecycle context manager.

Converted from Talend tPrejob / tPostjob pattern.
Wraps each job execution with logging and status tracking.
"""
import logging
from contextlib import contextmanager

from snowflake.snowpark import Session

logger = logging.getLogger("etl")


def _sanitize(value: str) -> str:
    return value.replace("'", "''")


@contextmanager
def etl_job_context(job_name: str, session: Session):
    safe_name = _sanitize(job_name)
    logger.info("Starting job: %s", job_name)
    session.sql(
        f"INSERT INTO ETL_LOG (JOB_NAME, START_TS, STATUS) "
        f"VALUES ('{safe_name}', CURRENT_TIMESTAMP(), 'RUNNING')"
    ).collect()
    try:
        yield session
        session.sql(
            f"UPDATE ETL_LOG SET STATUS='SUCCESS', END_TS=CURRENT_TIMESTAMP() "
            f"WHERE JOB_NAME='{safe_name}' AND STATUS='RUNNING'"
        ).collect()
        logger.info("Job completed: %s", job_name)
    except Exception:
        session.sql(
            f"UPDATE ETL_LOG SET STATUS='FAILED', END_TS=CURRENT_TIMESTAMP() "
            f"WHERE JOB_NAME='{safe_name}' AND STATUS='RUNNING'"
        ).collect()
        logger.exception("Job failed: %s", job_name)
        raise

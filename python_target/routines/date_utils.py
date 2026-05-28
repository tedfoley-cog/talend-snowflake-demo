"""Converted from: routines/DateFormatUtils.java

Date formatting utilities for ETL processing.
Used by: customer_dimension_load, cfpb_extract, regulatory_archive
"""
from datetime import datetime


def parse_date(date_str: str | None, pattern: str) -> datetime | None:
    if not date_str or not date_str.strip():
        return None
    py_pattern = _java_to_python_pattern(pattern)
    try:
        return datetime.strptime(date_str.strip(), py_pattern)
    except ValueError as e:
        raise ValueError(
            f"Failed to parse date '{date_str}' with pattern '{pattern}'"
        ) from e


def format_date(dt: datetime | None, pattern: str) -> str:
    if dt is None:
        return ""
    py_pattern = _java_to_python_pattern(pattern)
    return dt.strftime(py_pattern)


def convert_date_format(
    date_str: str | None, from_pattern: str, to_pattern: str
) -> str:
    dt = parse_date(date_str, from_pattern)
    return format_date(dt, to_pattern) if dt else ""


def get_fiscal_quarter(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    month = dt.month
    year = dt.year
    if month >= 10:
        return f"Q1-FY{year + 1}"
    if month >= 7:
        return f"Q4-FY{year}"
    if month >= 4:
        return f"Q3-FY{year}"
    return f"Q2-FY{year}"


def _java_to_python_pattern(pattern: str) -> str:
    return (
        pattern.replace("yyyy", "%Y")
        .replace("MM", "%m")
        .replace("dd", "%d")
        .replace("HH", "%H")
        .replace("mm", "%M")
        .replace("ss", "%S")
    )

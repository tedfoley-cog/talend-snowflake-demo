"""Converted from: routines/AccountValidator.java

Account and identity validation utilities.
Used by: customer_extract, customer_validation, dedup_customer
"""
import re

SSN_PATTERN = re.compile(r"^\d{3}-\d{2}-\d{4}$")
SSN_NUMERIC = re.compile(r"^\d{9}$")
ACCOUNT_PATTERN = re.compile(r"^[A-Z]{2}\d{10}$")


def is_valid_ssn(ssn: str | None) -> bool:
    if not ssn or not ssn.strip():
        return False
    cleaned = ssn.replace("-", "")
    if not SSN_NUMERIC.match(cleaned):
        return False
    area = cleaned[:3]
    group = cleaned[3:5]
    serial = cleaned[5:9]
    if area == "000" or area == "666" or area.startswith("9"):
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False
    return True


def format_ssn(ssn: str | None) -> str | None:
    if ssn is None:
        return None
    cleaned = re.sub(r"[^0-9]", "", ssn)
    if len(cleaned) != 9:
        return ssn
    return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"


def is_valid_account_number(account_num: str | None) -> bool:
    if account_num is None:
        return False
    return bool(ACCOUNT_PATTERN.match(account_num.strip().upper()))


def luhn_check(number: str | None) -> bool:
    if not number:
        return False
    cleaned = re.sub(r"[^0-9]", "", number)
    if not cleaned:
        return False
    total = 0
    alternate = False
    for ch in reversed(cleaned):
        digit = int(ch)
        if alternate:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        alternate = not alternate
    return total % 10 == 0


def mask_field(value: str | None, show_last: int) -> str | None:
    if value is None or len(value) <= show_last:
        return value
    masked = ""
    for ch in value[: len(value) - show_last]:
        masked += "*" if ch.isdigit() else ch
    masked += value[len(value) - show_last :]
    return masked

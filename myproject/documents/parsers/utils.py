import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dateutil import parser as date_parser

DATE_FORMATS = (
    '%Y-%m-%d',
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%d-%m-%Y',
    '%m-%d-%Y',
    '%d.%m.%Y',
    '%Y/%m/%d',
)

AMOUNT_PATTERN = re.compile(r'[^\d.\-]')


def parse_date(value: str | None) -> date | None:
    if not value or not str(value).strip():
        return None

    cleaned = str(value).strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    try:
        parsed = date_parser.parse(cleaned, dayfirst=False)
        return parsed.date()
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        parsed = date_parser.parse(cleaned, dayfirst=True)
        return parsed.date()
    except (ValueError, TypeError, OverflowError):
        return None


def parse_amount(value: str | None) -> Decimal | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    negative = cleaned.startswith('(') and cleaned.endswith(')')
    if negative:
        cleaned = cleaned[1:-1]

    cleaned = AMOUNT_PATTERN.sub('', cleaned)
    if not cleaned or cleaned in ('-', '.'):
        return None

    try:
        amount = Decimal(cleaned)
        return -amount if negative else amount
    except InvalidOperation:
        return None


def normalize_currency(value: str | None, default: str = 'USD') -> str | None:
    if not value or not str(value).strip():
        return default

    cleaned = str(value).strip().upper()
    cleaned = re.sub(r'[^A-Z]', '', cleaned)
    return cleaned[:3] if cleaned else default


def normalize_header(header: str) -> str:
    return re.sub(r'[\s_]+', '', header.strip().lower())

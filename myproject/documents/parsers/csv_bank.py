import csv
import io
from collections import Counter
from decimal import Decimal

from documents.parsers.exceptions import ParseError
from documents.parsers.types import ParsedBankTransaction, ParsedDocument
from documents.parsers.utils import normalize_currency, normalize_header, parse_amount, parse_date

COLUMN_ALIASES = {
    'date': {'date', 'csvdate', 'transactiondate', 'txdate'},
    'description': {'description', 'desc', 'narration', 'details', 'memo'},
    'debit': {'debit', 'withdrawal', 'withdrawals', 'amountout'},
    'credit': {'credit', 'deposit', 'deposits', 'amountin'},
    'balance': {'balance', 'runningbalance', 'closingbalance'},
    'currency': {'currency', 'curr', 'ccy'},
}


def _resolve_column(normalized_headers: dict[str, str], field: str) -> str | None:
    aliases = COLUMN_ALIASES[field]
    for header, normalized in normalized_headers.items():
        if normalized in aliases:
            return header
    return None


def _get_row_value(row: dict, column: str | None) -> str | None:
    if not column:
        return None
    value = row.get(column)
    if value is None:
        return None
    return str(value).strip() or None


def parse_csv_bank_statement(file_bytes: bytes) -> ParsedDocument:
    try:
        text = file_bytes.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ParseError(f'CSV is not valid UTF-8: {exc}') from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ParseError('CSV has no headers')

    normalized_headers = {
        header: normalize_header(header)
        for header in reader.fieldnames
        if header
    }

    date_col = _resolve_column(normalized_headers, 'date')
    desc_col = _resolve_column(normalized_headers, 'description')
    debit_col = _resolve_column(normalized_headers, 'debit')
    credit_col = _resolve_column(normalized_headers, 'credit')
    balance_col = _resolve_column(normalized_headers, 'balance')
    currency_col = _resolve_column(normalized_headers, 'currency')

    if not date_col and not desc_col:
        raise ParseError('CSV must contain at least date or description columns')

    transactions: list[ParsedBankTransaction] = []
    currencies: list[str] = []
    dates = []
    vendors: list[str] = []

    for row in reader:
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue

        raw_date = _get_row_value(row, date_col)
        raw_desc = _get_row_value(row, desc_col) or ''
        raw_debit = _get_row_value(row, debit_col)
        raw_credit = _get_row_value(row, credit_col)
        raw_balance = _get_row_value(row, balance_col)
        raw_currency = _get_row_value(row, currency_col)

        txn_date = parse_date(raw_date)
        if txn_date:
            dates.append(txn_date)

        currency = normalize_currency(raw_currency)
        if currency:
            currencies.append(currency)

        if raw_desc:
            vendors.append(raw_desc.split()[0] if raw_desc else '')

        transactions.append(
            ParsedBankTransaction(
                transaction_date=txn_date,
                description=raw_desc,
                debit=parse_amount(raw_debit),
                credit=parse_amount(raw_credit),
                balance=parse_amount(raw_balance),
                currency=currency,
            )
        )

    if not transactions:
        raise ParseError('CSV contains no transaction rows')

    dominant_currency = None
    if currencies:
        dominant_currency = Counter(currencies).most_common(1)[0][0]

    document_date = min(dates) if dates else None
    vendor = vendors[0] if vendors else None

    total_debits = sum(
        (t.debit for t in transactions if t.debit is not None),
        start=Decimal('0'),
    )
    total_credits = sum(
        (t.credit for t in transactions if t.credit is not None),
        start=Decimal('0'),
    )

    net = Decimal('0')
    if total_credits:
        net += total_credits
    if total_debits:
        net -= total_debits

    return ParsedDocument(
        vendor=vendor,
        document_date=document_date,
        total_amount=net if net else None,
        currency=dominant_currency or 'USD',
        metadata={'transaction_count': len(transactions)},
        transactions=transactions,
    )

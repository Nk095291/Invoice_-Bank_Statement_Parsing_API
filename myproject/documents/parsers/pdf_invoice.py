import io
import re

import pdfplumber

from documents.parsers.exceptions import ParseError
from documents.parsers.types import ParsedDocument, ParsedLineItem
from documents.parsers.utils import normalize_currency, parse_amount, parse_date

INVOICE_NUMBER_PATTERN = re.compile(
    r'invoice\s*#?\s*:?\s*([A-Za-z0-9\-]+)',
    re.IGNORECASE,
)
VENDOR_PATTERN = re.compile(r'vendor\s*:?\s*(.+)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'date\s*:?\s*(.+)', re.IGNORECASE)
CURRENCY_PATTERN = re.compile(r'currency\s*:?\s*([A-Za-z]{3})', re.IGNORECASE)
LINE_ITEM_PATTERN = re.compile(
    r'^\s*[-•]\s*(.+?)\s+\$?\s*([\d,]+\.?\d*)\s*$',
)
SUBTOTAL_PATTERN = re.compile(r'subtotal\s*:?\s*\$?\s*([\d,]+\.?\d*)', re.IGNORECASE)
TAX_PATTERN = re.compile(r'tax\s*(?:\([^)]*\))?\s*:?\s*\$?\s*([\d,]+\.?\d*)', re.IGNORECASE)
TOTAL_PATTERN = re.compile(r'total\s*:?\s*\$?\s*([\d,]+\.?\d*)', re.IGNORECASE)


def _extract_text(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or '' for page in pdf.pages]
        text = '\n'.join(pages).strip()
        if not text:
            raise ParseError('PDF contains no extractable text')
        return text
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError(f'Failed to read PDF: {exc}') from exc


def parse_pdf_invoice(file_bytes: bytes) -> ParsedDocument:
    text = _extract_text(file_bytes)
    lines = text.splitlines()

    invoice_number = None
    vendor = None
    document_date = None
    currency = None
    subtotal = None
    tax = None
    total = None
    line_items: list[ParsedLineItem] = []
    in_line_items = False
    sort_order = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r'^line\s*items?\s*:?\s*$', stripped, re.IGNORECASE):
            in_line_items = True
            continue

        if in_line_items:
            if re.match(r'^(subtotal|tax|total)\b', stripped, re.IGNORECASE):
                in_line_items = False
            else:
                item_match = LINE_ITEM_PATTERN.match(stripped)
                if item_match:
                    description = item_match.group(1).strip()
                    amount = parse_amount(item_match.group(2))
                    if amount is not None:
                        line_items.append(
                            ParsedLineItem(
                                description=description,
                                amount=amount,
                                sort_order=sort_order,
                            )
                        )
                        sort_order += 1
                continue

        inv_match = INVOICE_NUMBER_PATTERN.search(stripped)
        if inv_match and not invoice_number:
            invoice_number = inv_match.group(1).strip()

        vendor_match = VENDOR_PATTERN.search(stripped)
        if vendor_match and not vendor:
            vendor = vendor_match.group(1).strip()

        date_match = DATE_PATTERN.search(stripped)
        if date_match and not document_date:
            document_date = parse_date(date_match.group(1).strip())

        currency_match = CURRENCY_PATTERN.search(stripped)
        if currency_match and not currency:
            currency = normalize_currency(currency_match.group(1))

        if re.match(r'^\s*subtotal\b', stripped, re.IGNORECASE):
            subtotal_match = SUBTOTAL_PATTERN.search(stripped)
            if subtotal_match and subtotal is None:
                subtotal = parse_amount(subtotal_match.group(1))
            continue

        tax_match = TAX_PATTERN.search(stripped)
        if tax_match and tax is None:
            tax = parse_amount(tax_match.group(1))

        if re.match(r'^\s*total\b', stripped, re.IGNORECASE):
            total_match = TOTAL_PATTERN.search(stripped)
            if total_match and total is None:
                total = parse_amount(total_match.group(1))

    metadata = {}
    if invoice_number:
        metadata['invoice_number'] = invoice_number
    if subtotal is not None:
        metadata['subtotal'] = str(subtotal)
    if tax is not None:
        metadata['tax'] = str(tax)

    return ParsedDocument(
        vendor=vendor,
        document_date=document_date,
        total_amount=total,
        currency=currency or 'USD',
        metadata=metadata,
        line_items=line_items,
    )

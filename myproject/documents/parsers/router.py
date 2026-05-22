from documents.models import DocumentType
from documents.parsers.csv_bank import parse_csv_bank_statement
from documents.parsers.pdf_invoice import parse_pdf_invoice
from documents.parsers.types import ParsedDocument


def parse_document(document_type: str, file_bytes: bytes) -> ParsedDocument:
    if document_type == DocumentType.INVOICE_PDF:
        return parse_pdf_invoice(file_bytes)
    if document_type == DocumentType.BANK_STATEMENT_CSV:
        return parse_csv_bank_statement(file_bytes)
    raise ValueError(f'Unsupported document type: {document_type}')

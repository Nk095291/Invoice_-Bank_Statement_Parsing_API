import hashlib
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from core.logging import get_logger
from documents.models import (
    BankTransaction,
    Document,
    DocumentStatus,
    DocumentType,
    LineItem,
)
from documents.parsers.exceptions import ParseError
from documents.parsers.router import parse_document
from documents.parsers.types import ParsedDocument

User = get_user_model()
logger = get_logger('documents.service')


class DuplicateDocumentError(Exception):
    def __init__(self, existing_doc_id: str):
        self.existing_doc_id = existing_doc_id
        super().__init__('Duplicate document')


class DocumentService:
    @staticmethod
    def compute_content_hash(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def infer_document_type(filename: str) -> str | None:
        lower = filename.lower()
        if lower.endswith('.pdf'):
            return DocumentType.INVOICE_PDF
        if lower.endswith('.csv'):
            return DocumentType.BANK_STATEMENT_CSV
        return None

    @staticmethod
    def resolve_user(user_id_header: str | None) -> User | None:
        if not user_id_header:
            return None
        try:
            user_id = int(user_id_header.strip())
        except (ValueError, TypeError):
            logger.warning('Invalid X-User-Id header', extra={'user_id': user_id_header})
            return None
        # TODO : make sure the user exists in the database
        return User.objects.filter(pk=user_id).first()

    def check_duplicate(self, content_hash: str) -> Document | None:
        return Document.objects.filter(
            content_hash=content_hash,
            is_deleted=False,
        ).first()

    @transaction.atomic
    def upload(
        self,
        file_bytes: bytes,
        filename: str,
        user_id_header: str | None = None,
    ) -> Document:
        content_hash = self.compute_content_hash(file_bytes)
        existing = self.check_duplicate(content_hash)
        if existing:
            logger.info(
                'Duplicate upload detected',
                extra={
                    'content_hash': content_hash,
                    'doc_id': str(existing.doc_id),
                },
            )
            raise DuplicateDocumentError(str(existing.doc_id))

        document_type = self.infer_document_type(filename)
        if not document_type:
            raise ValueError('Unsupported file type')

        user = self.resolve_user(user_id_header)

        document = Document(
            content_hash=content_hash,
            user=user,
            document_type=document_type,
            status=DocumentStatus.PROCESSING,
            original_filename=filename,
        )
        document.file.save(filename, ContentFile(file_bytes), save=False)
        document.save()

        logger.info(
            'Upload accepted',
            extra={
                'doc_id': str(document.doc_id),
                'user_id': user.pk if user else None,
                'event': 'upload',
            },
        )

        try:
            parsed = parse_document(document_type, file_bytes)
            self._apply_parsed_data(document, parsed)
            document.status = DocumentStatus.COMPLETED
            document.error_message = ''
            document.save()
            logger.info(
                'Parsing completed',
                extra={'doc_id': str(document.doc_id), 'event': 'parse_success'},
            )
        except (ParseError, ValueError) as exc:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            document.save()
            logger.error(
                'Parsing failed',
                extra={'doc_id': str(document.doc_id), 'event': 'parse_failure'},
                exc_info=True,
            )

        return document

    def _apply_parsed_data(self, document: Document, parsed: ParsedDocument) -> None:
        document.vendor = parsed.vendor
        document.document_date = parsed.document_date
        document.total_amount = parsed.total_amount
        document.currency = parsed.currency
        document.metadata = parsed.metadata
        document.save()

        if document.document_type == DocumentType.INVOICE_PDF:
            LineItem.objects.filter(document=document).delete()
            LineItem.objects.bulk_create([
                LineItem(
                    document=document,
                    description=item.description,
                    amount=item.amount,
                    quantity=item.quantity,
                    sort_order=item.sort_order,
                )
                for item in parsed.line_items
            ])
        elif document.document_type == DocumentType.BANK_STATEMENT_CSV:
            BankTransaction.objects.filter(document=document).delete()
            BankTransaction.objects.bulk_create([
                BankTransaction(
                    document=document,
                    transaction_date=txn.transaction_date,
                    description=txn.description,
                    debit=txn.debit,
                    credit=txn.credit,
                    balance=txn.balance,
                    currency=txn.currency,
                )
                for txn in parsed.transactions
            ])

    def get_document(self, doc_id: str) -> Document | None:
        try:
            return Document.objects.prefetch_related(
                'line_items',
                'transactions',
            ).get(doc_id=doc_id, is_deleted=False)
        except Document.DoesNotExist:
            return None

    def update_document(self, doc_id: str, data: dict[str, Any]) -> Document | None:
        document = self.get_document(doc_id)
        if not document:
            return None

        allowed_fields = {'vendor', 'document_date', 'currency', 'metadata'}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(document, field, value)

        document.save()
        logger.info('Document updated', extra={'doc_id': str(document.doc_id)})
        return document

    def soft_delete(self, doc_id: str) -> bool:
        document = self.get_document(doc_id)
        if not document:
            return False

        if document.file:
            document.file.delete(save=False)

        document.is_deleted = True
        document.deleted_at = timezone.now()
        document.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

        logger.info('Document soft-deleted', extra={'doc_id': str(document.doc_id)})
        return True

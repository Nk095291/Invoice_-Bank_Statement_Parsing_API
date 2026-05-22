import hashlib
import os
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import QuerySet
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
from documents.parsers.utils import parse_date

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
        return User.objects.filter(pk=user_id).first()

    def check_duplicate(self, content_hash: str) -> Document | None:
        return Document.objects.filter(
            content_hash=content_hash,
            is_deleted=False,
        ).first()

    def _enqueue_parse(self, doc_id: str) -> None:
        if os.getenv('SYNC_PARSE', '').lower() in ('true', '1', 'yes'):
            self.parse_and_persist(doc_id)
            return
        from documents.tasks import parse_document_task

        parse_document_task.delay(doc_id)

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

        transaction.on_commit(lambda: self._enqueue_parse(str(document.doc_id)))

        return document

    def parse_and_persist(self, doc_id: str) -> Document:
        document = Document.objects.get(doc_id=doc_id, is_deleted=False)

        if not document.file:
            document.status = DocumentStatus.FAILED
            document.error_message = 'No file attached to document'
            document.save()
            return document

        with document.file.open('rb') as file_handle:
            file_bytes = file_handle.read()

        try:
            parsed = parse_document(document.document_type, file_bytes)
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

    def list_documents(
        self,
        filters: dict[str, Any] | None = None,
        user_id_header: str | None = None,
    ) -> QuerySet:
        queryset = Document.objects.filter(is_deleted=False).order_by('-created_at')

        user = self.resolve_user(user_id_header)
        if user:
            queryset = queryset.filter(user=user)

        if not filters:
            return queryset

        vendor = filters.get('vendor')
        if vendor:
            queryset = queryset.filter(vendor__icontains=vendor)

        date_from = filters.get('date_from')
        if date_from:
            queryset = queryset.filter(document_date__gte=date_from)

        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(document_date__lte=date_to)

        amount_min = filters.get('amount_min')
        if amount_min is not None:
            queryset = queryset.filter(total_amount__gte=amount_min)

        amount_max = filters.get('amount_max')
        if amount_max is not None:
            queryset = queryset.filter(total_amount__lte=amount_max)

        currency = filters.get('currency')
        if currency:
            queryset = queryset.filter(currency=currency.upper())

        document_type = filters.get('document_type')
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        status = filters.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @staticmethod
    def parse_list_filters(query_params) -> dict[str, Any]:
        filters: dict[str, Any] = {}

        if query_params.get('vendor'):
            filters['vendor'] = query_params['vendor'].strip()

        if query_params.get('date_from'):
            parsed = parse_date(query_params['date_from'])
            if parsed:
                filters['date_from'] = parsed

        if query_params.get('date_to'):
            parsed = parse_date(query_params['date_to'])
            if parsed:
                filters['date_to'] = parsed

        if query_params.get('amount_min'):
            try:
                filters['amount_min'] = Decimal(query_params['amount_min'])
            except InvalidOperation:
                pass

        if query_params.get('amount_max'):
            try:
                filters['amount_max'] = Decimal(query_params['amount_max'])
            except InvalidOperation:
                pass

        if query_params.get('currency'):
            filters['currency'] = query_params['currency'].strip()

        if query_params.get('document_type'):
            filters['document_type'] = query_params['document_type'].strip()

        if query_params.get('status'):
            filters['status'] = query_params['status'].strip()

        return filters

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
            try:
                document.file.delete(save=False)
            except OSError as exc:
                logger.warning(
                    'Could not delete media file',
                    extra={'doc_id': str(document.doc_id), 'error': str(exc)},
                )

        document.is_deleted = True
        document.deleted_at = timezone.now()
        document.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

        logger.info('Document soft-deleted', extra={'doc_id': str(document.doc_id)})
        return True

import uuid

from django.conf import settings
from django.db import models


class DocumentType(models.TextChoices):
    INVOICE_PDF = 'invoice_pdf', 'Invoice PDF'
    BANK_STATEMENT_CSV = 'bank_statement_csv', 'Bank Statement CSV'


class DocumentStatus(models.TextChoices):
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Document(models.Model):
    doc_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_hash = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
    )
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    status = models.CharField(
        max_length=16,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PROCESSING,
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/%Y/%m/')
    vendor = models.CharField(max_length=255, null=True, blank=True)
    document_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['content_hash'],
                condition=models.Q(is_deleted=False),
                name='unique_active_content_hash',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['vendor']),
            models.Index(fields=['document_date']),
            models.Index(fields=['currency']),
            models.Index(fields=['document_type']),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.doc_id} ({self.document_type})'


class LineItem(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    description = models.CharField(max_length=512)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    quantity = models.CharField(max_length=64, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self) -> str:
        return f'{self.description}: {self.amount}'


class BankTransaction(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=512, blank=True, default='')
    debit = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    credit = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)

    class Meta:
        ordering = ['transaction_date', 'id']

    def __str__(self) -> str:
        return f'{self.transaction_date}: {self.description}'

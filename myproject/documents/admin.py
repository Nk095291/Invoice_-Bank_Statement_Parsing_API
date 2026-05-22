from django.contrib import admin

from documents.models import BankTransaction, Document, LineItem


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 0


class BankTransactionInline(admin.TabularInline):
    model = BankTransaction
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'doc_id',
        'document_type',
        'status',
        'vendor',
        'document_date',
        'total_amount',
        'currency',
        'user',
        'created_at',
    )
    list_filter = ('document_type', 'status', 'currency')
    search_fields = ('doc_id', 'vendor', 'content_hash', 'original_filename')
    readonly_fields = ('doc_id', 'content_hash', 'created_at', 'updated_at')
    inlines = [LineItemInline, BankTransactionInline]

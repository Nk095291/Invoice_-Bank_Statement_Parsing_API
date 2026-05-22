from django.conf import settings
from rest_framework import serializers

from documents.models import BankTransaction, Document, LineItem


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name:
            raise serializers.ValidationError('Filename is required.')

        extension = '.' + value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
        if extension not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise serializers.ValidationError(
                f'Unsupported file type. Allowed: {", ".join(settings.ALLOWED_UPLOAD_EXTENSIONS)}'
            )

        content_type = getattr(value, 'content_type', '') or ''
        if (
            content_type
            and content_type not in settings.ALLOWED_UPLOAD_MIME_TYPES
            and extension not in settings.ALLOWED_UPLOAD_EXTENSIONS
        ):
            raise serializers.ValidationError(f'Unsupported MIME type: {content_type}')

        if value.size == 0:
            raise serializers.ValidationError('File is empty.')

        if value.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise serializers.ValidationError(
                f'File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB.'
            )

        return value


class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ['description', 'amount', 'quantity', 'sort_order']


class BankTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = [
            'transaction_date',
            'description',
            'debit',
            'credit',
            'balance',
            'currency',
        ]


class DocumentProcessingSerializer(serializers.Serializer):
    doc_id = serializers.UUIDField()
    status = serializers.CharField()
    detail = serializers.CharField()


class DocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'doc_id',
            'document_type',
            'status',
            'original_filename',
            'vendor',
            'document_date',
            'total_amount',
            'currency',
            'user_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class DocumentDetailSerializer(serializers.ModelSerializer):
    line_items = LineItemSerializer(many=True, read_only=True)
    transactions = BankTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            'doc_id',
            'document_type',
            'status',
            'original_filename',
            'vendor',
            'document_date',
            'total_amount',
            'currency',
            'error_message',
            'metadata',
            'user_id',
            'line_items',
            'transactions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class DocumentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['vendor', 'document_date', 'currency', 'metadata']


class DocumentUploadResponseSerializer(serializers.Serializer):
    doc_id = serializers.UUIDField()
    status = serializers.CharField()

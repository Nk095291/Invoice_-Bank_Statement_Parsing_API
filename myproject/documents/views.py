from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import get_logger
from documents.models import DocumentStatus
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentProcessingSerializer,
    DocumentUpdateSerializer,
    DocumentUploadResponseSerializer,
    DocumentUploadSerializer,
)
from documents.services.document_service import DocumentService
from documents.utils import parse_doc_id

logger = get_logger('documents.api')
document_service = DocumentService()


class DocumentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DocumentDetailMixin:
    def _invalid_doc_id_response(self):
        return Response(
            {'detail': 'Invalid document id format.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _resolve_doc_id(self, doc_id: str) -> str | None:
        parsed = parse_doc_id(doc_id)
        if not parsed:
            return None
        return str(parsed)


class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        file_bytes = uploaded_file.read()
        user_id_header = request.headers.get('X-User-Id')

        logger.info(
            'Upload request received',
            extra={
                'event': 'upload_request',
                'user_id': user_id_header,
                'filename': uploaded_file.name,
            },
        )

        document = document_service.upload(
            file_bytes=file_bytes,
            filename=uploaded_file.name,
            user_id_header=user_id_header,
        )

        response_data = DocumentUploadResponseSerializer({
            'doc_id': document.doc_id,
            'status': document.status,
        }).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class DocumentListView(APIView):
    pagination_class = DocumentPagination

    def get(self, request):
        filters = document_service.parse_list_filters(request.query_params)
        user_id_header = request.headers.get('X-User-Id')
        queryset = document_service.list_documents(filters, user_id_header)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DocumentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class DocumentDetailView(DocumentDetailMixin, APIView):
    def get(self, request, doc_id):
        resolved = self._resolve_doc_id(doc_id)
        if not resolved:
            return self._invalid_doc_id_response()

        document = document_service.get_document(resolved)
        if not document:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if document.status == DocumentStatus.PROCESSING:
            return Response(
                DocumentProcessingSerializer({
                    'doc_id': document.doc_id,
                    'status': document.status,
                    'detail': 'Document is still being processed.',
                }).data,
                status=status.HTTP_200_OK,
            )

        return Response(DocumentDetailSerializer(document).data)

    def patch(self, request, doc_id):
        resolved = self._resolve_doc_id(doc_id)
        if not resolved:
            return self._invalid_doc_id_response()

        document = document_service.get_document(resolved)
        if not document:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentUpdateSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = document_service.update_document(
            resolved,
            serializer.validated_data,
        )
        return Response(DocumentDetailSerializer(updated).data)

    def delete(self, request, doc_id):
        resolved = self._resolve_doc_id(doc_id)
        if not resolved:
            return self._invalid_doc_id_response()

        deleted = document_service.soft_delete(resolved)
        if not deleted:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import get_logger
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentUpdateSerializer,
    DocumentUploadResponseSerializer,
    DocumentUploadSerializer,
)
from documents.services.document_service import DocumentService

logger = get_logger('documents.api')
document_service = DocumentService()


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


class DocumentDetailView(APIView):
    def get(self, request, doc_id):
        document = document_service.get_document(str(doc_id))
        if not document:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentDetailSerializer(document).data)

    def patch(self, request, doc_id):
        document = document_service.get_document(str(doc_id))
        if not document:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentUpdateSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = document_service.update_document(
            str(doc_id),
            serializer.validated_data,
        )
        return Response(DocumentDetailSerializer(updated).data)

    def delete(self, request, doc_id):
        deleted = document_service.soft_delete(str(doc_id))
        if not deleted:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

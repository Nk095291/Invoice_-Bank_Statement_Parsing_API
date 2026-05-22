from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from documents.services.document_service import DuplicateDocumentError


def custom_exception_handler(exc, context):
    if isinstance(exc, DuplicateDocumentError):
        return Response(
            {
                'detail': 'Duplicate document',
                'doc_id': exc.existing_doc_id,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return exception_handler(exc, context)

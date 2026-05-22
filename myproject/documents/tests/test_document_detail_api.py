import uuid

from documents.models import Document, DocumentStatus, DocumentType
from documents.tests.base import DocumentsApiTestCase


class DocumentDetailApiTest(DocumentsApiTestCase):
    """
    Test cases for document detail API (GET, PATCH, DELETE).

    - Ensures GET completed document returns 200 with parsed data
    - Ensures GET processing document returns still processing message
    - Ensures invalid doc_id format returns 400
    - Ensures unknown doc_id returns 404
    - Ensures PATCH updates metadata
    - Ensures DELETE returns 204
    - Ensures DELETE on already deleted document returns 404
    """

    def test_DocumentDetailView__CompletedDocument__Returns200WithData(self):
        """Ensures GET on completed document returns full payload."""
        # Given
        upload = self.upload_sample('invoice_acme.pdf')
        doc_id = upload.data['doc_id']
        self.wait_for_parse(doc_id)

        # When
        response = self.client.get(self.detail_url(doc_id))

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual('completed', response.data['status'])
        self.assertEqual('Acme Corp', response.data['vendor'])
        self.assertTrue(len(response.data['line_items']) >= 1)

    def test_DocumentDetailView__ProcessingDocument__ReturnsStillProcessingMessage(self):
        """Ensures GET on processing document returns processing message."""
        # Given
        document = Document.objects.create(
            content_hash='a' * 64,
            document_type=DocumentType.INVOICE_PDF,
            status=DocumentStatus.PROCESSING,
            original_filename='pending.pdf',
        )
        doc_id = str(document.doc_id)

        # When
        response = self.client.get(self.detail_url(doc_id))

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual('processing', response.data['status'])
        self.assertEqual('Document is still being processed.', response.data['detail'])
        self.assertNotIn('line_items', response.data)

    def test_DocumentDetailView__InvalidDocIdFormat__Returns400(self):
        """Ensures incomplete UUID returns 400 invalid format."""
        # Given
        invalid_doc_id = '43ee75e4-5f6a-4c12-9c02-30fb60ea446'

        # When
        response = self.client.get(self.detail_url(invalid_doc_id))

        # Then
        self.assertEqual(400, response.status_code)
        self.assertEqual('Invalid document id format.', response.data['detail'])

    def test_DocumentDetailView__UnknownDocId__Returns404(self):
        """Ensures valid UUID not in database returns 404."""
        # Given
        unknown_doc_id = str(uuid.uuid4())

        # When
        response = self.client.get(self.detail_url(unknown_doc_id))

        # Then
        self.assertEqual(404, response.status_code)
        self.assertEqual('Not found.', response.data['detail'])

    def test_DocumentDetailView__PatchMetadata__Returns200Updated(self):
        """Ensures PATCH updates vendor and currency."""
        # Given
        upload = self.upload_sample('invoice_acme.pdf')
        doc_id = upload.data['doc_id']
        self.wait_for_parse(doc_id)
        payload = {'vendor': 'Acme Corporation', 'currency': 'EUR'}

        # When
        response = self.client.patch(
            self.detail_url(doc_id),
            payload,
            format='json',
        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual('Acme Corporation', response.data['vendor'])
        self.assertEqual('EUR', response.data['currency'])

    def test_DocumentDetailView__DeleteDocument__Returns204(self):
        """Ensures DELETE soft-deletes document and returns 204."""
        # Given
        upload = self.upload_sample('invoice_acme.pdf')
        doc_id = upload.data['doc_id']

        # When
        response = self.client.delete(self.detail_url(doc_id))

        # Then
        self.assertEqual(204, response.status_code)

    def test_DocumentDetailView__DeleteAlreadyDeleted__Returns404(self):
        """Ensures DELETE on already deleted document returns 404."""
        # Given
        upload = self.upload_sample('invoice_acme.pdf')
        doc_id = upload.data['doc_id']
        self.client.delete(self.detail_url(doc_id))

        # When
        response = self.client.delete(self.detail_url(doc_id))

        # Then
        self.assertEqual(404, response.status_code)

    def test_DocumentDetailView__InvalidDocIdOnDelete__Returns400(self):
        """Ensures DELETE with invalid doc_id returns 400."""
        # Given
        invalid_doc_id = 'not-a-valid-uuid'

        # When
        response = self.client.delete(self.detail_url(invalid_doc_id))

        # Then
        self.assertEqual(400, response.status_code)

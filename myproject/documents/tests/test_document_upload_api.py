from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import Document, DocumentStatus
from documents.tests.base import DocumentsApiTestCase, SAMPLES_DIR


class DocumentUploadApiTest(DocumentsApiTestCase):
    """
    Test cases for document upload API.

    - Ensures upload without file returns 400
    - Ensures upload with empty file returns 400
    - Ensures successful PDF upload returns 201 with processing status
    - Ensures duplicate upload returns 409 with existing doc_id
    - Ensures unsupported file type returns 400
    """

    def test_DocumentUploadView__NoFileProvided__Returns400(self):
        """Ensures POST without file field returns 400."""
        # Given
        payload = {}

        # When
        response = self.client.post(self.upload_url, payload, format='multipart')

        # Then
        self.assertEqual(400, response.status_code)

    def test_DocumentUploadView__EmptyFileProvided__Returns400(self):
        """Ensures POST with empty file returns 400."""
        # Given
        empty_file = SimpleUploadedFile('empty.pdf', b'', content_type='application/pdf')

        # When
        response = self.client.post(
            self.upload_url,
            {'file': empty_file},
            format='multipart',
        )

        # Then
        self.assertEqual(400, response.status_code)

    def test_DocumentUploadView__ValidPdfUpload__Returns201Processing(self):
        """Ensures valid PDF upload returns 201 with processing status."""
        # Given
        filename = 'invoice_acme.pdf'

        # When
        response = self.upload_sample(filename, user_id=self.user.pk)

        # Then
        self.assertEqual(201, response.status_code)
        self.assertEqual('processing', response.data['status'])
        self.assertIn('doc_id', response.data)

    def test_DocumentUploadView__ValidPdfUploadAfterParse__DocumentCompleted(self):
        """Ensures document completes parsing after background task runs."""
        # Given
        response = self.upload_sample('invoice_acme.pdf', user_id=self.user.pk)
        doc_id = response.data['doc_id']

        # When
        document = self.wait_for_parse(doc_id)

        # Then
        self.assertEqual(DocumentStatus.COMPLETED, document.status)
        self.assertEqual('Acme Corp', document.vendor)

    def test_DocumentUploadView__DuplicateUpload__Returns409(self):
        """Ensures uploading the same file twice returns 409 with existing doc_id."""
        # Given
        first = self.upload_sample('invoice_acme.pdf')
        doc_id = first.data['doc_id']

        # When
        second = self.upload_sample('invoice_acme.pdf')

        # Then
        self.assertEqual(409, second.status_code)
        self.assertEqual('Duplicate document', second.data['detail'])
        self.assertEqual(doc_id, second.data['doc_id'])

    def test_DocumentUploadView__UnsupportedFileType__Returns400(self):
        """Ensures unsupported file extension returns 400."""
        # Given
        bad_file = SimpleUploadedFile(
            'notes.txt',
            b'hello',
            content_type='text/plain',
        )

        # When
        response = self.client.post(
            self.upload_url,
            {'file': bad_file},
            format='multipart',
        )

        # Then
        self.assertEqual(400, response.status_code)

    def test_DocumentUploadView__ValidCsvUpload__Returns201Processing(self):
        """Ensures valid CSV upload returns 201 with processing status."""
        # Given
        filename = 'bank_statement.csv'

        # When
        response = self.upload_sample(filename)

        # Then
        self.assertEqual(201, response.status_code)
        self.assertEqual('processing', response.data['status'])

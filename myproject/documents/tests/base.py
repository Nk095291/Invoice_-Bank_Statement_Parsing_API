from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()
SAMPLES_DIR = settings.BASE_DIR.parent / 'samples'


class DocumentsApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )
        self.upload_url = '/documents/upload/'
        self.list_url = '/documents/'

    def detail_url(self, doc_id):
        return f'/documents/{doc_id}/'

    def upload_sample(self, filename, user_id=None):
        path = SAMPLES_DIR / filename
        with path.open('rb') as file_handle:
            headers = {}
            if user_id is not None:
                headers['X-User-Id'] = str(user_id)
            with self.captureOnCommitCallbacks(execute=True):
                return self.client.post(
                    self.upload_url,
                    {'file': file_handle},
                    format='multipart',
                    headers=headers,
                )

    def wait_for_parse(self, doc_id):
        from documents.models import Document, DocumentStatus

        document = Document.objects.get(doc_id=doc_id)
        if document.status == DocumentStatus.PROCESSING:
            from documents.services.document_service import DocumentService

            DocumentService().parse_and_persist(str(doc_id))
            document.refresh_from_db()
        return document

from decimal import Decimal

from documents.models import Document, DocumentStatus, DocumentType
from documents.tests.base import DocumentsApiTestCase


class DocumentListApiTest(DocumentsApiTestCase):
    """
    Test cases for document list API with search and filtering.

    - Ensures list returns all non-deleted documents
    - Ensures vendor filter matches case-insensitively
    - Ensures date range filter works
    - Ensures amount range filter works
    - Ensures currency, document_type, and status filters work
    - Ensures combined filters use AND logic
    - Ensures no matches returns empty results page
    """

    @classmethod
    def setUpTestData(cls):
        Document.objects.create(
            content_hash='1' * 64,
            document_type=DocumentType.INVOICE_PDF,
            status=DocumentStatus.COMPLETED,
            original_filename='a.pdf',
            vendor='Acme Corp',
            document_date='2024-01-15',
            total_amount=Decimal('770.00'),
            currency='USD',
        )
        Document.objects.create(
            content_hash='2' * 64,
            document_type=DocumentType.BANK_STATEMENT_CSV,
            status=DocumentStatus.COMPLETED,
            original_filename='b.csv',
            vendor='Globex Inc',
            document_date='2024-02-01',
            total_amount=Decimal('120.50'),
            currency='EUR',
        )
        Document.objects.create(
            content_hash='3' * 64,
            document_type=DocumentType.INVOICE_PDF,
            status=DocumentStatus.FAILED,
            original_filename='c.pdf',
            vendor='Other Vendor',
            document_date='2024-03-10',
            total_amount=Decimal('50.00'),
            currency='USD',
            is_deleted=True,
        )

    def test_DocumentListView__NoFilters__ReturnsActiveDocuments(self):
        """Ensures list returns only non-deleted documents."""
        # Given
        expected_count = 2

        # When
        response = self.client.get(self.list_url)

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_count, response.data['count'])

    def test_DocumentListView__VendorFilter__ReturnsMatchingDocuments(self):
        """Ensures vendor query param filters by icontains."""
        # Given
        expected_vendor = 'Acme Corp'

        # When
        response = self.client.get(self.list_url, {'vendor': 'acme'})

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(expected_vendor, response.data['results'][0]['vendor'])

    def test_DocumentListView__DateRangeFilter__ReturnsMatchingDocuments(self):
        """Ensures date_from and date_to filter document_date inclusively."""
        # Given
        expected_count = 1

        # When
        response = self.client.get(
            self.list_url,
            {'date_from': '2024-01-01', 'date_to': '2024-01-31'},
        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_count, response.data['count'])

    def test_DocumentListView__AmountRangeFilter__ReturnsMatchingDocuments(self):
        """Ensures amount_min and amount_max filter total_amount."""
        # Given
        expected_count = 1

        # When
        response = self.client.get(
            self.list_url,
            {'amount_min': '700', 'amount_max': '800'},
        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_count, response.data['count'])

    def test_DocumentListView__CurrencyFilter__ReturnsMatchingDocuments(self):
        """Ensures currency filter matches exactly."""
        # Given
        expected_currency = 'EUR'

        # When
        response = self.client.get(self.list_url, {'currency': 'eur'})

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(expected_currency, response.data['results'][0]['currency'])

    def test_DocumentListView__DocumentTypeFilter__ReturnsMatchingDocuments(self):
        """Ensures document_type filter matches exactly."""
        # Given
        expected_type = DocumentType.BANK_STATEMENT_CSV

        # When
        response = self.client.get(
            self.list_url,
            {'document_type': expected_type},
        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(expected_type, response.data['results'][0]['document_type'])

    def test_DocumentListView__StatusFilter__ReturnsMatchingDocuments(self):
        """Ensures status filter matches exactly."""
        # Given
        expected_status = DocumentStatus.COMPLETED

        # When
        response = self.client.get(self.list_url, {'status': expected_status})

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, response.data['count'])

    def test_DocumentListView__CombinedFilters__ReturnsAndMatch(self):
        """Ensures multiple filters combine with AND logic."""
        # Given
        expected_vendor = 'Acme Corp'

        # When
        response = self.client.get(
            self.list_url,
            {
                'vendor': 'Acme',
                'currency': 'USD',
                'document_type': DocumentType.INVOICE_PDF,
            },
        )

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(expected_vendor, response.data['results'][0]['vendor'])

    def test_DocumentListView__NoMatches__ReturnsEmptyResults(self):
        """Ensures filters with no matches return empty paginated results."""
        # Given
        expected_count = 0

        # When
        response = self.client.get(self.list_url, {'vendor': 'NonexistentVendorXYZ'})

        # Then
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_count, response.data['count'])

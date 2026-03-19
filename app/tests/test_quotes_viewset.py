"""Tests for app/api/viewsets/quotes.py — QuoteRequest, Quote, PublicQuoteRequest viewsets."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class GenerateQuoteTest(SimpleTestCase):
    """Test QuoteRequestViewSet.generate_quote action."""

    @patch('app.api.viewsets.quotes.generate_unique_reference', return_value='QT-2026-12345')
    @patch('app.api.viewsets.quotes.Quote')
    def test_creates_quote_with_unique_reference(self, MockQuote, mock_gen_ref):
        from app.api.viewsets.quotes import QuoteRequestViewSet

        quote_request = MagicMock()
        quote_request.id = 1
        # hasattr check for existing quote should return False
        del quote_request.quote

        created_quote = MagicMock()
        created_quote.id = 10
        created_quote.reference_number = 'QT-2026-12345'
        created_quote.amount = 500
        created_quote.tax_amount = 25
        created_quote.valid_until = '2026-12-31'
        created_quote.status = 'DRAFT'
        MockQuote.objects.create.return_value = created_quote
        MockQuote.Status.DRAFT = 'DRAFT'

        viewset = QuoteRequestViewSet()
        viewset.get_object = MagicMock(return_value=quote_request)
        viewset.kwargs = {'pk': 1}

        request = MagicMock()
        request.data = {
            'amount': 500,
            'tax_amount': 25,
            'valid_until': '2026-12-31',
            'terms': 'Net 30',
        }
        request.user = MagicMock()

        response = viewset.generate_quote(request, pk=1)

        self.assertEqual(response.status_code, 201)
        mock_gen_ref.assert_called_once_with('QT', MockQuote)
        self.assertEqual(response.data['reference_number'], 'QT-2026-12345')

    def test_rejects_duplicate_quote(self):
        from app.api.viewsets.quotes import QuoteRequestViewSet

        quote_request = MagicMock()
        quote_request.quote = MagicMock()  # Already has a quote

        viewset = QuoteRequestViewSet()
        viewset.get_object = MagicMock(return_value=quote_request)

        request = MagicMock()
        request.data = {'amount': 500, 'valid_until': '2026-12-31'}

        response = viewset.generate_quote(request, pk=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.data['detail'])

    def test_rejects_missing_required_fields(self):
        from app.api.viewsets.quotes import QuoteRequestViewSet

        quote_request = MagicMock()
        del quote_request.quote

        viewset = QuoteRequestViewSet()
        viewset.get_object = MagicMock(return_value=quote_request)

        request = MagicMock()
        request.data = {'terms': 'Net 30'}  # missing amount and valid_until

        response = viewset.generate_quote(request, pk=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('required', response.data['detail'])


class QuoteViewSetSendTest(SimpleTestCase):
    """Test QuoteViewSet.send action."""

    @patch('app.models.Notification')
    def test_send_marks_as_sent(self, MockNotification):
        from app.api.viewsets.quotes import QuoteViewSet

        quote = MagicMock()
        quote.id = 1
        quote.status = 'DRAFT'
        quote.reference_number = 'QT-2026-00001'
        quote.quote_request.client.user = MagicMock()

        with patch('app.api.viewsets.quotes.Quote') as MockQuote:
            MockQuote.Status.DRAFT = 'DRAFT'
            MockQuote.Status.SENT = 'SENT'

            viewset = QuoteViewSet()
            viewset.get_object = MagicMock(return_value=quote)

            request = MagicMock()
            response = viewset.send(request, pk=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(quote.status, 'SENT')
        quote.save.assert_called_once()

    def test_send_rejects_non_draft(self):
        from app.api.viewsets.quotes import QuoteViewSet

        quote = MagicMock()
        quote.status = 'SENT'

        with patch('app.api.viewsets.quotes.Quote') as MockQuote:
            MockQuote.Status.DRAFT = 'DRAFT'

            viewset = QuoteViewSet()
            viewset.get_object = MagicMock(return_value=quote)

            request = MagicMock()
            response = viewset.send(request, pk=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('Cannot send', response.data['detail'])


class PublicQuoteRequestProcessTest(SimpleTestCase):
    """Test PublicQuoteRequestViewSet.process action."""

    def test_process_marks_as_processed(self):
        from app.api.viewsets.quotes import PublicQuoteRequestViewSet

        pqr = MagicMock()
        pqr.id = 1
        pqr.processed = False

        viewset = PublicQuoteRequestViewSet()
        viewset.get_object = MagicMock(return_value=pqr)

        request = MagicMock()
        request.data = {'admin_notes': 'Processed by admin'}
        request.user = MagicMock()

        response = viewset.process(request, pk=1)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(pqr.processed)
        self.assertEqual(pqr.admin_notes, 'Processed by admin')
        pqr.save.assert_called_once()

    def test_process_rejects_already_processed(self):
        from app.api.viewsets.quotes import PublicQuoteRequestViewSet

        pqr = MagicMock()
        pqr.processed = True

        viewset = PublicQuoteRequestViewSet()
        viewset.get_object = MagicMock(return_value=pqr)

        request = MagicMock()
        response = viewset.process(request, pk=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('Already processed', response.data['detail'])

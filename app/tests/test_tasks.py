"""Tests for app/tasks.py — Celery task functions."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _mock_quote(status='SENT'):
    """Build a mock Quote with related objects."""
    user = MagicMock()
    user.get_full_name.return_value = 'John Doe'
    user.username = 'johndoe'
    user.email = 'john@example.com'

    client = MagicMock()
    client.user = user

    quote_request = MagicMock()
    quote_request.client = client
    quote_request.service_type.name = 'Medical Interpretation'

    quote = MagicMock()
    quote.id = 1
    quote.status = status
    quote.reference_number = 'QT-2026-12345'
    quote.amount = 500
    quote.tax_amount = 25
    quote.valid_until = '2026-12-31'
    quote.quote_request = quote_request
    return quote


def _mock_assignment(status='CONFIRMED'):
    """Build a mock Assignment with related objects."""
    interp_user = MagicMock()
    interp_user.get_full_name.return_value = 'Jane Smith'
    interp_user.username = 'janesmith'
    interp_user.email = 'jane@example.com'

    interpreter = MagicMock()
    interpreter.user = interp_user

    assignment = MagicMock()
    assignment.id = 10
    assignment.status = status
    assignment.interpreter = interpreter
    assignment.service_type.name = 'Legal Interpretation'
    assignment.start_time = '2026-07-01T09:00:00'
    assignment.end_time = '2026-07-01T11:00:00'
    assignment.location = '123 Main St'
    assignment.city = 'Boston'
    assignment.state = 'MA'
    assignment.zip_code = '02101'
    assignment.source_language.name = 'Spanish'
    assignment.target_language.name = 'English'
    return assignment


class SendQuoteStatusEmailTest(SimpleTestCase):
    """Test send_quote_status_email task."""

    @patch('app.tasks.send_mail')
    @patch('app.tasks.render_to_string', return_value='<html>quote</html>')
    def test_sends_email_for_sent_status(self, mock_render, mock_send_mail):
        quote = _mock_quote(status='SENT')

        with patch('app.models.Quote') as MockQuote:
            MockQuote.objects.select_related.return_value.get.return_value = quote

            from app.tasks import send_quote_status_email
            send_quote_status_email(1)

        mock_render.assert_called_once()
        template_name = mock_render.call_args[0][0]
        self.assertEqual(template_name, 'emails/quote_sent.html')

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]
        self.assertIn('JHBRIDGE', call_kwargs['subject'])
        self.assertEqual(call_kwargs['recipient_list'], ['john@example.com'])

    @patch('app.tasks.send_mail')
    @patch('app.tasks.render_to_string')
    def test_skips_draft_status(self, mock_render, mock_send_mail):
        quote = _mock_quote(status='DRAFT')

        with patch('app.models.Quote') as MockQuote:
            MockQuote.objects.select_related.return_value.get.return_value = quote

            from app.tasks import send_quote_status_email
            send_quote_status_email(1)

        mock_render.assert_not_called()
        mock_send_mail.assert_not_called()

    @patch('app.tasks.logger')
    def test_handles_exception_gracefully(self, mock_logger):
        with patch('app.models.Quote') as MockQuote:
            MockQuote.objects.select_related.return_value.get.side_effect = Exception('DB error')

            from app.tasks import send_quote_status_email
            send_quote_status_email(999)

        mock_logger.error.assert_called_once()


class SendAssignmentStatusEmailTest(SimpleTestCase):
    """Test send_assignment_status_email task."""

    @patch('app.tasks.send_mail')
    @patch('app.tasks.render_to_string', return_value='<html>assignment</html>')
    def test_sends_email_for_confirmed_status(self, mock_render, mock_send_mail):
        assignment = _mock_assignment(status='CONFIRMED')

        with patch('app.models.Assignment') as MockAssignment:
            MockAssignment.objects.select_related.return_value.get.return_value = assignment

            from app.tasks import send_assignment_status_email
            send_assignment_status_email(10)

        mock_render.assert_called_once()
        template_name = mock_render.call_args[0][0]
        self.assertEqual(template_name, 'emails/assignment_confirmed.html')

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args[1]
        self.assertEqual(call_kwargs['recipient_list'], ['jane@example.com'])

    @patch('app.tasks.send_mail')
    @patch('app.tasks.render_to_string')
    def test_skips_when_no_interpreter(self, mock_render, mock_send_mail):
        assignment = _mock_assignment(status='PENDING')
        assignment.interpreter = None

        with patch('app.models.Assignment') as MockAssignment:
            MockAssignment.objects.select_related.return_value.get.return_value = assignment

            from app.tasks import send_assignment_status_email
            send_assignment_status_email(10)

        mock_send_mail.assert_not_called()

    @patch('app.tasks.logger')
    def test_handles_exception_gracefully(self, mock_logger):
        with patch('app.models.Assignment') as MockAssignment:
            MockAssignment.objects.select_related.return_value.get.side_effect = Exception('DB error')

            from app.tasks import send_assignment_status_email
            send_assignment_status_email(999)

        mock_logger.error.assert_called_once()

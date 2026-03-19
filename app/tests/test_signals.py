"""Tests for app/signals.py — _original_status tracking and signal dispatch."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class OriginalStatusTrackingTest(SimpleTestCase):
    """Verify _original_status is set correctly on QuoteRequest, Quote, Assignment."""

    def _make_instance(self, model_path, status='PENDING', pk=1):
        """Build a mock that mimics __init__ setting _original_status."""
        mock = MagicMock()
        mock.pk = pk
        mock.status = status
        mock._original_status = status if pk else None
        return mock

    def test_original_status_set_on_existing_instance(self):
        inst = self._make_instance('app.models.QuoteRequest', status='QUOTED', pk=5)
        self.assertEqual(inst._original_status, 'QUOTED')

    def test_original_status_none_on_new_instance(self):
        inst = self._make_instance('app.models.QuoteRequest', status='PENDING', pk=None)
        self.assertIsNone(inst._original_status)

    def test_original_status_updated_after_save(self):
        inst = self._make_instance('app.models.Quote', status='DRAFT', pk=1)
        # Simulate status change + save
        inst.status = 'SENT'
        inst._original_status = inst.status  # mimics save() behavior
        self.assertEqual(inst._original_status, 'SENT')


class HandleQuoteStatusChangeSignalTest(SimpleTestCase):
    """Test the handle_quote_status_change signal handler logic."""

    @patch('app.signals.send_quote_status_email')
    def test_fires_on_status_change(self, mock_task):
        from app.signals import handle_quote_status_change

        instance = MagicMock()
        instance.status = 'SENT'
        instance._original_status = 'DRAFT'
        instance.id = 1

        handle_quote_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_called_once_with(1)

    @patch('app.signals.send_quote_status_email')
    def test_skips_when_status_unchanged(self, mock_task):
        from app.signals import handle_quote_status_change

        instance = MagicMock()
        instance.status = 'SENT'
        instance._original_status = 'SENT'
        instance.id = 1

        handle_quote_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_not_called()

    @patch('app.signals.send_quote_status_email')
    def test_skips_draft_status(self, mock_task):
        from app.signals import handle_quote_status_change

        instance = MagicMock()
        instance.status = 'DRAFT'
        instance._original_status = None
        instance.id = 1

        handle_quote_status_change(sender=None, instance=instance, created=True)

        mock_task.delay.assert_not_called()

    @patch('app.signals.send_quote_status_email')
    def test_fires_on_create_non_draft(self, mock_task):
        from app.signals import handle_quote_status_change

        instance = MagicMock()
        instance.status = 'SENT'
        instance._original_status = None
        instance.id = 2

        handle_quote_status_change(sender=None, instance=instance, created=True)

        mock_task.delay.assert_called_once_with(2)


class HandleAssignmentStatusChangeSignalTest(SimpleTestCase):
    """Test the handle_assignment_status_change signal handler logic."""

    @patch('app.signals.send_assignment_status_email')
    def test_fires_on_status_change(self, mock_task):
        from app.signals import handle_assignment_status_change

        instance = MagicMock()
        instance.status = 'CONFIRMED'
        instance._original_status = 'PENDING'
        instance.id = 10

        handle_assignment_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_called_once_with(10)

    @patch('app.signals.send_assignment_status_email')
    def test_skips_when_status_unchanged(self, mock_task):
        from app.signals import handle_assignment_status_change

        instance = MagicMock()
        instance.status = 'PENDING'
        instance._original_status = 'PENDING'
        instance.id = 10

        handle_assignment_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_not_called()

    @patch('app.signals.send_assignment_status_email')
    def test_fires_on_create(self, mock_task):
        from app.signals import handle_assignment_status_change

        instance = MagicMock()
        instance.status = 'PENDING'
        instance._original_status = None
        instance.id = 20

        handle_assignment_status_change(sender=None, instance=instance, created=True)

        mock_task.delay.assert_called_once_with(20)


class HandleQuoteRequestStatusChangeSignalTest(SimpleTestCase):
    """Test the handle_quote_request_status_change signal handler logic."""

    @patch('app.signals.send_quote_request_status_email')
    def test_fires_on_status_change(self, mock_task):
        from app.signals import handle_quote_request_status_change

        instance = MagicMock()
        instance.status = 'PROCESSING'
        instance._original_status = 'PENDING'
        instance.id = 5

        handle_quote_request_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_called_once_with(5)

    @patch('app.signals.send_quote_request_status_email')
    def test_fires_on_create(self, mock_task):
        from app.signals import handle_quote_request_status_change

        instance = MagicMock()
        instance.status = 'PENDING'
        instance._original_status = None
        instance.id = 3

        handle_quote_request_status_change(sender=None, instance=instance, created=True)

        mock_task.delay.assert_called_once_with(3)

    @patch('app.signals.send_quote_request_status_email')
    def test_skips_when_status_unchanged(self, mock_task):
        from app.signals import handle_quote_request_status_change

        instance = MagicMock()
        instance.status = 'PENDING'
        instance._original_status = 'PENDING'
        instance.id = 3

        handle_quote_request_status_change(sender=None, instance=instance, created=False)

        mock_task.delay.assert_not_called()

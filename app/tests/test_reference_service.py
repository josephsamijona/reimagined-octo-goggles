"""Tests for app/api/services/reference_service.py."""
import re
from unittest.mock import MagicMock, patch, call

from django.test import SimpleTestCase


class GenerateUniqueReferenceFormatTest(SimpleTestCase):
    """Test that generated references match the expected PREFIX-YYYY-XXXXX format."""

    @patch('app.api.services.reference_service.timezone')
    def test_format_with_qt_prefix(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        model.objects.filter.return_value.exists.return_value = False

        from app.api.services.reference_service import generate_unique_reference
        result = generate_unique_reference('QT', model)

        self.assertRegex(result, r'^QT-2026-\d{5}$')

    @patch('app.api.services.reference_service.timezone')
    def test_format_with_inv_prefix(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        model.objects.filter.return_value.exists.return_value = False

        from app.api.services.reference_service import generate_unique_reference
        result = generate_unique_reference('INV', model, 'invoice_number')

        self.assertRegex(result, r'^INV-2026-\d{5}$')

    @patch('app.api.services.reference_service.timezone')
    def test_format_with_ps_prefix(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        model.objects.filter.return_value.exists.return_value = False

        from app.api.services.reference_service import generate_unique_reference
        result = generate_unique_reference('PS', model, 'document_number')

        self.assertRegex(result, r'^PS-2026-\d{5}$')


class GenerateUniqueReferenceCollisionTest(SimpleTestCase):
    """Test that the loop retries when first attempt collides."""

    @patch('app.api.services.reference_service.timezone')
    def test_retries_on_collision(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        # First call returns True (collision), second returns False (unique)
        model.objects.filter.return_value.exists.side_effect = [True, False]

        from app.api.services.reference_service import generate_unique_reference
        result = generate_unique_reference('QT', model)

        # Should have called filter twice
        self.assertEqual(model.objects.filter.call_count, 2)
        # Result should still be valid format
        self.assertRegex(result, r'^QT-2026-\d{5}$')

    @patch('app.api.services.reference_service.timezone')
    def test_uses_correct_field_name(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        model.objects.filter.return_value.exists.return_value = False

        from app.api.services.reference_service import generate_unique_reference
        generate_unique_reference('INV', model, 'invoice_number')

        # Verify the filter was called with the right field name
        filter_kwargs = model.objects.filter.call_args[1]
        self.assertIn('invoice_number', filter_kwargs)

    @patch('app.api.services.reference_service.timezone')
    def test_uses_default_field_name(self, mock_tz):
        mock_tz.now.return_value.year = 2026

        model = MagicMock()
        model.objects.filter.return_value.exists.return_value = False

        from app.api.services.reference_service import generate_unique_reference
        generate_unique_reference('QT', model)

        filter_kwargs = model.objects.filter.call_args[1]
        self.assertIn('reference_number', filter_kwargs)

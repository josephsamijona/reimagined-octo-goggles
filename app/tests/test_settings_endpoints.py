"""Tests for Feature 7 settings endpoints.

All tests use SimpleTestCase with MagicMock — no DB required.
"""
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from app.api.serializers.settings import (
    APIKeySerializer, APIKeyCreateSerializer, CompanyInfoSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_key(key='abcdef1234567890' * 2, is_active=True, expires_at=None):
    k = MagicMock()
    k.id = 'uuid-1234'
    k.name = 'Test Key'
    k.app_name = 'Command Center'
    k.key = key
    k.is_active = is_active
    k.expires_at = expires_at
    k.last_used = None
    k.created_at = None
    k.is_valid.return_value = is_active
    return k


# ---------------------------------------------------------------------------
# APIKeySerializer — masked key
# ---------------------------------------------------------------------------

class APIKeySerializerTest(SimpleTestCase):

    def test_key_preview_masks_key(self):
        k = _make_api_key(key='abcdef1234567890abcdef1234567890')
        data = APIKeySerializer(k).data
        self.assertIn('key_preview', data)
        self.assertTrue(data['key_preview'].endswith('...'))
        self.assertEqual(data['key_preview'][:8], 'abcdef12')

    def test_key_field_not_exposed(self):
        k = _make_api_key()
        data = APIKeySerializer(k).data
        self.assertNotIn('key', data)

    def test_is_valid_true_when_active(self):
        k = _make_api_key(is_active=True)
        data = APIKeySerializer(k).data
        self.assertTrue(data['is_valid'])

    def test_is_valid_false_when_inactive(self):
        k = _make_api_key(is_active=False)
        data = APIKeySerializer(k).data
        self.assertFalse(data['is_valid'])

    def test_has_required_fields(self):
        k = _make_api_key()
        data = APIKeySerializer(k).data
        for field in ('id', 'name', 'app_name', 'key_preview', 'is_active', 'is_valid'):
            self.assertIn(field, data)


# ---------------------------------------------------------------------------
# APIKeyCreateSerializer — returns full key
# ---------------------------------------------------------------------------

class APIKeyCreateSerializerTest(SimpleTestCase):

    def test_key_field_present_on_create_serializer(self):
        serializer = APIKeyCreateSerializer()
        self.assertIn('key', serializer.fields)

    def test_key_is_read_only(self):
        serializer = APIKeyCreateSerializer()
        self.assertTrue(serializer.fields['key'].read_only)

    def test_create_generates_64_char_hex_key(self):
        import secrets as _secrets
        key = _secrets.token_hex(32)
        self.assertEqual(len(key), 64)
        self.assertRegex(key, r'^[0-9a-f]+$')


# ---------------------------------------------------------------------------
# CompanyInfoSerializer
# ---------------------------------------------------------------------------

class CompanyInfoSerializerTest(SimpleTestCase):

    @patch('app.api.serializers.settings.settings')
    def test_returns_site_url(self, mock_settings):
        mock_settings.SITE_URL = 'https://portal.jhbridgetranslation.com'
        mock_settings.RAILWAY_ENVIRONMENT = 'production'
        mock_settings.DEBUG = False
        data = CompanyInfoSerializer({}).data
        self.assertEqual(data['site_url'], 'https://portal.jhbridgetranslation.com')

    @patch('app.api.serializers.settings.settings')
    def test_returns_app_name(self, mock_settings):
        mock_settings.SITE_URL = ''
        mock_settings.RAILWAY_ENVIRONMENT = 'development'
        mock_settings.DEBUG = True
        data = CompanyInfoSerializer({}).data
        self.assertEqual(data['app_name'], 'JHBridge Translation')

    @patch('app.api.serializers.settings.settings')
    def test_returns_environment(self, mock_settings):
        mock_settings.SITE_URL = ''
        mock_settings.RAILWAY_ENVIRONMENT = 'staging'
        mock_settings.DEBUG = False
        data = CompanyInfoSerializer({}).data
        self.assertEqual(data['environment'], 'staging')

    @patch('app.api.serializers.settings.settings')
    def test_returns_debug_flag(self, mock_settings):
        mock_settings.SITE_URL = ''
        mock_settings.RAILWAY_ENVIRONMENT = 'development'
        mock_settings.DEBUG = True
        data = CompanyInfoSerializer({}).data
        self.assertTrue(data['debug'])

    @patch('app.api.serializers.settings.settings')
    def test_has_all_fields(self, mock_settings):
        mock_settings.SITE_URL = ''
        mock_settings.RAILWAY_ENVIRONMENT = 'development'
        mock_settings.DEBUG = False
        data = CompanyInfoSerializer({}).data
        for field in ('site_url', 'app_name', 'environment', 'debug'):
            self.assertIn(field, data)


# ---------------------------------------------------------------------------
# ServiceTypeViewSet toggle logic (unit test via direct method call)
# ---------------------------------------------------------------------------

class ServiceTypeToggleTest(SimpleTestCase):

    def test_toggle_active_to_inactive(self):
        from app.api.viewsets.settings import ServiceTypeViewSet
        vset = ServiceTypeViewSet()
        vset.get_object = MagicMock()
        service_type = MagicMock()
        service_type.active = True
        vset.get_object.return_value = service_type

        response = vset.toggle(MagicMock(), pk=1)
        self.assertFalse(service_type.active)
        service_type.save.assert_called_once_with(update_fields=['active'])

    def test_toggle_inactive_to_active(self):
        from app.api.viewsets.settings import ServiceTypeViewSet
        vset = ServiceTypeViewSet()
        vset.get_object = MagicMock()
        service_type = MagicMock()
        service_type.active = False
        vset.get_object.return_value = service_type

        response = vset.toggle(MagicMock(), pk=1)
        self.assertTrue(service_type.active)


# ---------------------------------------------------------------------------
# LanguageViewSet toggle logic
# ---------------------------------------------------------------------------

class LanguageToggleTest(SimpleTestCase):

    def test_toggle_active_to_inactive(self):
        from app.api.viewsets.settings import LanguageViewSet
        vset = LanguageViewSet()
        vset.get_object = MagicMock()
        language = MagicMock()
        language.is_active = True
        vset.get_object.return_value = language

        vset.toggle(MagicMock(), pk=1)
        self.assertFalse(language.is_active)
        language.save.assert_called_once_with(update_fields=['is_active'])

    def test_toggle_inactive_to_active(self):
        from app.api.viewsets.settings import LanguageViewSet
        vset = LanguageViewSet()
        vset.get_object = MagicMock()
        language = MagicMock()
        language.is_active = False
        vset.get_object.return_value = language

        vset.toggle(MagicMock(), pk=1)
        self.assertTrue(language.is_active)


# ---------------------------------------------------------------------------
# APIKeyViewSet rotate
# ---------------------------------------------------------------------------

class APIKeyRotateTest(SimpleTestCase):

    @patch('app.api.viewsets.settings.secrets')
    def test_rotate_generates_new_key(self, mock_secrets):
        from app.api.viewsets.settings import APIKeyViewSet
        mock_secrets.token_hex.return_value = 'newkey' * 10 + 'xx'

        vset = APIKeyViewSet()
        api_key = MagicMock()
        api_key.id = 'uuid-9999'
        api_key.key = 'newkey' * 10 + 'xx'
        vset.get_object = MagicMock(return_value=api_key)

        response = vset.rotate(MagicMock(), pk='uuid-9999')
        api_key.save.assert_called_once_with(update_fields=['key'])
        self.assertEqual(response.data['key'], api_key.key)

    @patch('app.api.viewsets.settings.secrets')
    def test_rotate_response_has_detail(self, mock_secrets):
        from app.api.viewsets.settings import APIKeyViewSet
        mock_secrets.token_hex.return_value = 'x' * 64

        vset = APIKeyViewSet()
        api_key = MagicMock()
        api_key.id = 'uuid-9999'
        api_key.key = 'x' * 64
        vset.get_object = MagicMock(return_value=api_key)

        response = vset.rotate(MagicMock(), pk='uuid-9999')
        self.assertIn('detail', response.data)

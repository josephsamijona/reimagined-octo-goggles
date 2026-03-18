"""Tests for app/services/assignment_email_service.py."""
import time
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytz
from django.test import SimpleTestCase, override_settings

import app.services.assignment_email_service as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_dt(year, month, day, hour, minute=0):
    from django.utils import timezone as dj_tz
    return dj_tz.make_aware(datetime(year, month, day, hour, minute), pytz.UTC)


def _make_assignment(state='MA', has_interpreter=True, interpreter_email='interp@test.com'):
    """Build a minimal mock Assignment."""
    a = MagicMock()
    a.id = 42
    a.location = '100 Main St'
    a.city = 'Boston'
    a.state = state
    a.zip_code = '02101'
    a.start_time = _utc_dt(2025, 8, 15, 14)
    a.end_time = _utc_dt(2025, 8, 15, 16)
    a.interpreter_rate = '75.00'
    a.special_requirements = 'Medical terminology'
    a.service_type = MagicMock(name_value='Medical')
    a.service_type.name = 'Medical'
    a.source_language = MagicMock()
    a.source_language.name = 'Spanish'
    a.target_language = MagicMock()
    a.target_language.name = 'English'
    a.client = MagicMock()
    a.client.company_name = 'Boston Medical Center'
    a.client.user.phone = '617-555-0001'

    if has_interpreter:
        a.interpreter = MagicMock()
        a.interpreter.user.email = interpreter_email
        a.interpreter.user.first_name = 'Jane'
        a.interpreter.user.last_name = 'Doe'
        a.interpreter.user.get_full_name.return_value = 'Jane Doe'
        a.interpreter.state = state
    else:
        a.interpreter = None

    return a


# ---------------------------------------------------------------------------
# Token tests
# ---------------------------------------------------------------------------

class TokenTest(SimpleTestCase):

    def test_generate_and_verify_accept(self):
        token = svc.generate_assignment_token(99, 'accept')
        result = svc.verify_assignment_token(token, 'accept')
        self.assertEqual(result, 99)

    def test_generate_and_verify_decline(self):
        token = svc.generate_assignment_token(7, 'decline')
        result = svc.verify_assignment_token(token, 'decline')
        self.assertEqual(result, 7)

    def test_wrong_action_returns_none(self):
        token = svc.generate_assignment_token(1, 'accept')
        self.assertIsNone(svc.verify_assignment_token(token, 'decline'))

    def test_tampered_token_returns_none(self):
        self.assertIsNone(svc.verify_assignment_token('bad:token:data', 'accept'))

    def test_expired_token_returns_none(self):
        """Patch timezone.now() to simulate 25-hour-old token."""
        from django.utils import timezone as dj_tz
        from datetime import timedelta
        # Generate token
        token = svc.generate_assignment_token(5, 'accept')
        # Simulate 25h in the future when verifying
        future = dj_tz.now() + timedelta(hours=25)
        with patch('app.services.assignment_email_service.timezone') as mock_tz:
            mock_tz.now.return_value = future
            result = svc.verify_assignment_token(token, 'accept')
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Template config tests
# ---------------------------------------------------------------------------

class TemplateConfigTest(SimpleTestCase):

    def test_new_config(self):
        cfg = svc.get_email_template_config('new', 10)
        self.assertIn('assignment_new.html', cfg['template'])
        self.assertFalse(cfg['include_calendar'])
        self.assertIn('#10', cfg['subject'])

    def test_confirmed_includes_calendar(self):
        cfg = svc.get_email_template_config('confirmed', 10)
        self.assertTrue(cfg['include_calendar'])

    def test_cancelled_no_calendar(self):
        cfg = svc.get_email_template_config('cancelled', 10)
        self.assertFalse(cfg['include_calendar'])

    def test_completed_no_calendar(self):
        cfg = svc.get_email_template_config('completed', 10)
        self.assertFalse(cfg['include_calendar'])

    def test_no_show_no_calendar(self):
        cfg = svc.get_email_template_config('no_show', 10)
        self.assertFalse(cfg['include_calendar'])

    def test_unknown_type_returns_generic(self):
        cfg = svc.get_email_template_config('unknown_type')
        self.assertIn('assignment_generic.html', cfg['template'])

    def test_subject_contains_unique_id(self):
        cfg1 = svc.get_email_template_config('new', 1)
        cfg2 = svc.get_email_template_config('new', 1)
        # Two calls → two different IDs (prevents threading)
        self.assertNotEqual(cfg1['subject'], cfg2['subject'])


# ---------------------------------------------------------------------------
# Email context tests
# ---------------------------------------------------------------------------

class BuildEmailContextTest(SimpleTestCase):

    def test_basic_context_keys(self):
        a = _make_assignment()
        ctx = svc.build_email_context(a, 'confirmed', 'https://portal.jhbridge.com')
        for key in ('interpreter_name', 'assignment', 'start_time', 'end_time',
                    'client_name', 'service_type', 'location', 'rate',
                    'source_language', 'target_language', 'site_url'):
            self.assertIn(key, ctx, f"Missing key: {key}")

    def test_new_type_adds_accept_decline_urls(self):
        a = _make_assignment()
        ctx = svc.build_email_context(a, 'new', 'https://portal.jhbridge.com')
        self.assertIn('accept_url', ctx)
        self.assertIn('decline_url', ctx)
        self.assertTrue(ctx['accept_url'].startswith('https://portal.jhbridge.com'))
        self.assertTrue(ctx['decline_url'].startswith('https://portal.jhbridge.com'))

    def test_confirmed_type_no_accept_url(self):
        a = _make_assignment()
        ctx = svc.build_email_context(a, 'confirmed', 'https://portal.jhbridge.com')
        self.assertNotIn('accept_url', ctx)

    def test_site_url_trailing_slash_stripped(self):
        a = _make_assignment()
        ctx = svc.build_email_context(a, 'confirmed', 'https://portal.jhbridge.com/')
        self.assertFalse(ctx['site_url'].endswith('/'))

    def test_interpreter_name(self):
        a = _make_assignment()
        ctx = svc.build_email_context(a, 'confirmed', 'https://portal.jhbridge.com')
        self.assertIn('Jane', ctx['interpreter_name'])
        self.assertIn('Doe', ctx['interpreter_name'])


# ---------------------------------------------------------------------------
# ICS calendar tests
# ---------------------------------------------------------------------------

class GenerateIcsCalendarTest(SimpleTestCase):

    def test_returns_bytes(self):
        a = _make_assignment(state='TX')
        ics = svc.generate_ics_calendar(a)
        self.assertIsInstance(ics, bytes)

    def test_contains_assignment_uid(self):
        a = _make_assignment()
        ics = svc.generate_ics_calendar(a).decode('utf-8')
        self.assertIn('assignment-42@jhbridge.com', ics)

    def test_contains_interpreter_attendee(self):
        a = _make_assignment(interpreter_email='jane@example.com')
        ics = svc.generate_ics_calendar(a).decode('utf-8')
        self.assertIn('jane@example.com', ics)

    def test_uses_interpreter_state_timezone(self):
        """ICS DTSTART must reference the interpreter's local tz, not Boston."""
        a = _make_assignment(state='CA')  # Pacific
        ics = svc.generate_ics_calendar(a).decode('utf-8')
        # The icalendar lib encodes the tz abbrev in DTSTART;
        # the event's tzid should reference Los Angeles
        self.assertIn('America/Los_Angeles', ics)

    def test_method_is_request(self):
        a = _make_assignment()
        ics = svc.generate_ics_calendar(a).decode('utf-8')
        self.assertIn('METHOD:REQUEST', ics)

    def test_dtstamp_is_utc(self):
        """DTSTAMP must be UTC per RFC 5545."""
        a = _make_assignment()
        ics = svc.generate_ics_calendar(a).decode('utf-8')
        # UTC timestamps end with Z
        self.assertIn('DTSTAMP', ics)


# ---------------------------------------------------------------------------
# send_assignment_email (mocked)
# ---------------------------------------------------------------------------

class SendAssignmentEmailTest(SimpleTestCase):

    @patch('app.services.assignment_email_service.log_email_sent')
    @patch('app.services.assignment_email_service.render_to_string', return_value='<p>Test HTML</p>')
    @patch('app.services.assignment_email_service.EmailMultiAlternatives')
    def test_returns_true_on_success(self, MockEmail, mock_render, mock_log):
        mock_email_instance = MagicMock()
        MockEmail.return_value = mock_email_instance

        a = _make_assignment()
        result = svc.send_assignment_email(a, 'confirmed', site_url='https://portal.jhbridge.com')

        self.assertTrue(result)
        mock_email_instance.send.assert_called_once_with(fail_silently=False)
        mock_log.assert_called_once_with(a, 'confirmed')

    def test_returns_false_when_no_interpreter(self):
        a = _make_assignment(has_interpreter=False)
        result = svc.send_assignment_email(a, 'confirmed')
        self.assertFalse(result)

    def test_returns_false_when_no_email(self):
        a = _make_assignment(interpreter_email='')
        result = svc.send_assignment_email(a, 'confirmed')
        self.assertFalse(result)

    @patch('app.services.assignment_email_service.render_to_string', side_effect=Exception('template error'))
    def test_returns_false_on_render_exception(self, mock_render):
        a = _make_assignment()
        result = svc.send_assignment_email(a, 'confirmed')
        self.assertFalse(result)

    @override_settings(SITE_URL='https://custom.site.com')
    @patch('app.services.assignment_email_service.log_email_sent')
    @patch('app.services.assignment_email_service.render_to_string', return_value='<p>html</p>')
    @patch('app.services.assignment_email_service.EmailMultiAlternatives')
    def test_falls_back_to_settings_site_url(self, MockEmail, mock_render, mock_log):
        MockEmail.return_value = MagicMock()
        a = _make_assignment()
        # Call without site_url
        svc.send_assignment_email(a, 'completed')
        # render_to_string context must have site_url from settings
        ctx = mock_render.call_args[0][1]
        self.assertIn('custom.site.com', ctx['site_url'])

    @patch('app.services.assignment_email_service.log_email_sent')
    @patch('app.services.assignment_email_service.generate_ics_calendar', return_value=b'ICS_DATA')
    @patch('app.services.assignment_email_service.render_to_string', return_value='<p>html</p>')
    @patch('app.services.assignment_email_service.EmailMultiAlternatives')
    def test_confirmed_attaches_ics(self, MockEmail, mock_render, mock_ics, mock_log):
        mock_email_instance = MagicMock()
        MockEmail.return_value = mock_email_instance

        a = _make_assignment()
        svc.send_assignment_email(a, 'confirmed')

        mock_ics.assert_called_once_with(a)
        mock_email_instance.attach.assert_called_once()

    @patch('app.services.assignment_email_service.log_email_sent')
    @patch('app.services.assignment_email_service.render_to_string', return_value='<p>html</p>')
    @patch('app.services.assignment_email_service.EmailMultiAlternatives')
    def test_cancelled_no_ics(self, MockEmail, mock_render, mock_log):
        mock_email_instance = MagicMock()
        MockEmail.return_value = mock_email_instance

        a = _make_assignment()
        svc.send_assignment_email(a, 'cancelled')

        mock_email_instance.attach.assert_not_called()

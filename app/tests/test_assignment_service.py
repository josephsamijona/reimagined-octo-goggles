"""Tests for app/api/services/assignment_service.py."""
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytz
from django.test import SimpleTestCase, override_settings, TestCase


class CalculateTotalPaymentTest(SimpleTestCase):
    """Pure math tests."""

    def _call(self, rate, start, end, minimum):
        from app.api.services.assignment_service import calculate_total_payment
        return calculate_total_payment(rate, start, end, minimum)

    def _dt(self, hour):
        return datetime(2025, 7, 1, hour, 0, tzinfo=pytz.UTC)

    def test_normal_duration(self):
        result = self._call(50, self._dt(9), self._dt(11), 2)
        self.assertEqual(result, 100.0)

    def test_minimum_hours_applied(self):
        start = datetime(2025, 7, 1, 9, 0, tzinfo=pytz.UTC)
        end = datetime(2025, 7, 1, 9, 30, tzinfo=pytz.UTC)
        result = self._call(50, start, end, 2)
        self.assertEqual(result, 100.0)

    def test_rounding(self):
        start = datetime(2025, 7, 1, 9, 0, tzinfo=pytz.UTC)
        end = datetime(2025, 7, 1, 10, 20, tzinfo=pytz.UTC)
        result = self._call(75, start, end, 1.5)
        self.assertEqual(result, 112.5)


@override_settings(FASTAPI_BASE_URL='http://testserver-fastapi:8001')
class AddAssignmentToGoogleCalendarTest(SimpleTestCase):
    """Test the HTTP call to FastAPI calendar sync with mocked requests."""

    def _call(self, assignment_id):
        from app.api.services.assignment_service import add_assignment_to_google_calendar
        return add_assignment_to_google_calendar(assignment_id)

    @patch('app.api.services.assignment_service.requests.post')
    def test_success_returns_event_data(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {
            'event_id': 'abc123',
            'html_link': 'https://cal.google.com/event/abc123',
        }

        result = self._call(42)

        mock_post.assert_called_once_with(
            'http://testserver-fastapi:8001/calendar/sync-assignment',
            json={'assignment_id': 42},
            timeout=10,
        )
        self.assertEqual(result['event_id'], 'abc123')

    @patch('app.api.services.assignment_service.requests.post')
    def test_non_ok_response_returns_empty_dict(self, mock_post):
        mock_post.return_value.ok = False
        mock_post.return_value.status_code = 503
        mock_post.return_value.text = 'Service unavailable'

        result = self._call(99)
        self.assertEqual(result, {})

    @patch('app.api.services.assignment_service.requests.post')
    def test_network_error_returns_empty_dict(self, mock_post):
        import requests

        mock_post.side_effect = requests.RequestException('connection refused')
        result = self._call(7)
        self.assertEqual(result, {})

    @patch('app.api.services.assignment_service.requests.post')
    def test_trailing_slash_stripped_from_base_url(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {}

        with override_settings(FASTAPI_BASE_URL='http://localhost:8001/'):
            self._call(1)

        called_url = mock_post.call_args[0][0]
        self.assertFalse(called_url.startswith('http://localhost:8001//'))
        self.assertIn('/calendar/sync-assignment', called_url)


class CalendarEventBodyBuilderTest(SimpleTestCase):
    """Unit tests for app/api/services/calendar_service.py event builder."""

    class _Obj:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def _call(self, assignment):
        from app.api.services.calendar_service import _build_event_body

        return _build_event_body(assignment)

    def _base_assignment(self):
        user = self._Obj(first_name='Jane', last_name='Doe', email='jane@example.com')
        interpreter = self._Obj(user=user)
        client = self._Obj(company_name='Houston Medical Center')
        src_lang = self._Obj(name='Spanish')
        tgt_lang = self._Obj(name='English')
        service_type = self._Obj(name='Medical')

        return self._Obj(
            id=1,
            service_type=service_type,
            source_language=src_lang,
            target_language=tgt_lang,
            location='123 Main St',
            city='Houston',
            state='TX',
            zip_code='77001',
            start_time=datetime(2025, 7, 4, 9, 0, tzinfo=pytz.UTC),
            end_time=datetime(2025, 7, 4, 11, 0, tzinfo=pytz.UTC),
            client=client,
            client_name='',
            interpreter=interpreter,
            status='CONFIRMED',
            notes='Medical terminology required',
            interpreter_rate='75.00',
        )

    def test_state_drives_timezone(self):
        event = self._call(self._base_assignment())
        self.assertEqual(event['start']['timeZone'], 'America/Chicago')
        self.assertEqual(event['end']['timeZone'], 'America/Chicago')

    def test_california_timezone(self):
        assignment = self._base_assignment()
        assignment.state = 'CA'
        assignment.city = 'Los Angeles'
        event = self._call(assignment)
        self.assertEqual(event['start']['timeZone'], 'America/Los_Angeles')

    def test_unknown_state_falls_back_to_eastern(self):
        assignment = self._base_assignment()
        assignment.state = ''
        event = self._call(assignment)
        self.assertEqual(event['start']['timeZone'], 'America/New_York')

    def test_summary_format(self):
        event = self._call(self._base_assignment())
        self.assertIn('Medical', event['summary'])
        self.assertIn('Spanish', event['summary'])
        self.assertIn('English', event['summary'])

    def test_location_includes_zip(self):
        event = self._call(self._base_assignment())
        self.assertIn('77001', event['location'])

    def test_interpreter_email_as_attendee(self):
        event = self._call(self._base_assignment())
        self.assertIn('attendees', event)
        self.assertEqual(event['attendees'][0]['email'], 'jane@example.com')

    def test_no_attendee_when_no_email(self):
        assignment = self._base_assignment()
        assignment.interpreter.user.email = ''
        event = self._call(assignment)
        self.assertNotIn('attendees', event)

    def test_description_includes_rate_and_notes(self):
        event = self._call(self._base_assignment())
        desc = event['description']
        self.assertIn('$75.00/hr', desc)
        self.assertIn('Medical terminology required', desc)

    def test_two_reminders(self):
        event = self._call(self._base_assignment())
        minutes = [r['minutes'] for r in event['reminders']['overrides']]
        self.assertIn(60, minutes)
        self.assertIn(15, minutes)


class SharedConstantsTzForStateTest(SimpleTestCase):
    """Tests for shared/constants.py tz_for_state()."""

    def _call(self, state):
        from shared.constants import tz_for_state

        return tz_for_state(state)

    def test_texas_central(self):
        self.assertEqual(self._call('TX'), 'America/Chicago')

    def test_california_pacific(self):
        self.assertEqual(self._call('CA'), 'America/Los_Angeles')

    def test_empty_falls_back(self):
        self.assertEqual(self._call(''), 'America/New_York')

    def test_lowercase(self):
        self.assertEqual(self._call('fl'), 'America/New_York')

    def test_arizona_no_dst(self):
        self.assertEqual(self._call('AZ'), 'America/Phoenix')


class AssignmentNotificationEmailValidationTest(SimpleTestCase):
    """Tests for email validation in AssignmentNotificationService."""

    def test_validate_clean_email_valid(self):
        """Test that valid emails are accepted."""
        from app.services.assignment_notifications import AssignmentNotificationService

        valid_emails = [
            'user@example.com',
            'test.user@example.com',
            'test+tag@example.co.uk',
            'admin@sub.domain.com',
        ]

        for email in valid_emails:
            result = AssignmentNotificationService._validate_and_clean_email(email)
            self.assertEqual(result, email, f"Valid email {email} should be accepted")

    def test_validate_clean_email_with_spaces(self):
        """Test that emails with leading/trailing spaces are cleaned."""
        from app.services.assignment_notifications import AssignmentNotificationService

        email_with_spaces = '  user@example.com  '
        result = AssignmentNotificationService._validate_and_clean_email(email_with_spaces)
        self.assertEqual(result, 'user@example.com')

    def test_validate_clean_email_invalid(self):
        """Test that invalid emails are rejected."""
        from app.services.assignment_notifications import AssignmentNotificationService

        invalid_emails = [
            'not-an-email',
            'missing@',
            '@missing-local',
            'spaces in@email.com',
            'double@@domain.com',
            '',
            None,
        ]

        for email in invalid_emails:
            result = AssignmentNotificationService._validate_and_clean_email(email)
            self.assertIsNone(result, f"Invalid email {email} should be rejected")


class ResendEmailBackendValidationTest(SimpleTestCase):
    """Tests for email validation in ResendEmailBackend."""

    def test_clean_email_list_valid(self):
        """Test that valid emails are kept."""
        from app.utils.email_backend import ResendEmailBackend

        backend = ResendEmailBackend()
        emails = ['user1@example.com', 'user2@example.com']
        result = backend._clean_email_list(emails)
        self.assertEqual(result, emails)

    def test_clean_email_list_mixed(self):
        """Test that only valid emails are kept from mixed list."""
        from app.utils.email_backend import ResendEmailBackend

        backend = ResendEmailBackend()
        emails = ['valid@example.com', 'not-valid', 'another@test.com', '']
        result = backend._clean_email_list(emails)
        self.assertEqual(result, ['valid@example.com', 'another@test.com'])

    def test_clean_email_list_all_invalid(self):
        """Test that empty list is returned when all emails are invalid."""
        from app.utils.email_backend import ResendEmailBackend

        backend = ResendEmailBackend()
        emails = ['not-valid', '', 'missing@']
        result = backend._clean_email_list(emails)
        self.assertEqual(result, [])

    def test_clean_email_list_empty_input(self):
        """Test that empty input returns empty list."""
        from app.utils.email_backend import ResendEmailBackend

        backend = ResendEmailBackend()
        result = backend._clean_email_list([])
        self.assertEqual(result, [])
        result = backend._clean_email_list(None)
        self.assertEqual(result, [])

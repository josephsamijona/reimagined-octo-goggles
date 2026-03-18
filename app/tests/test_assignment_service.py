"""Tests for app/api/services/assignment_service.py."""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytz
from django.test import SimpleTestCase, override_settings


class CalculateTotalPaymentTest(SimpleTestCase):
    """Pure math — no DB needed."""

    def _call(self, rate, start, end, minimum):
        from app.api.services.assignment_service import calculate_total_payment
        return calculate_total_payment(rate, start, end, minimum)

    def _dt(self, hour):
        return datetime(2025, 7, 1, hour, 0, tzinfo=pytz.UTC)

    def test_normal_duration(self):
        result = self._call(50, self._dt(9), self._dt(11), 2)
        self.assertEqual(result, 100.0)

    def test_minimum_hours_applied(self):
        # 30-min mission but 2h minimum → billed 2h
        start = datetime(2025, 7, 1, 9, 0, tzinfo=pytz.UTC)
        end = datetime(2025, 7, 1, 9, 30, tzinfo=pytz.UTC)
        result = self._call(50, start, end, 2)
        self.assertEqual(result, 100.0)

    def test_rounding(self):
        # 1h20m @ $75 = 100 (minimum 1.5h) → 112.50
        start = datetime(2025, 7, 1, 9, 0, tzinfo=pytz.UTC)
        end = datetime(2025, 7, 1, 10, 20, tzinfo=pytz.UTC)
        result = self._call(75, start, end, 1.5)
        self.assertEqual(result, 112.5)


@override_settings(FASTAPI_BASE_URL='http://testserver-fastapi:8001')
class AddAssignmentToGoogleCalendarTest(SimpleTestCase):
    """Test the HTTP call to FastAPI calendar sync — no real network."""

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


class CalendarMapperTest(SimpleTestCase):
    """Unit tests for services/calendar_sync/mapper.py."""

    def _call(self, assignment):
        from services.calendar_sync.mapper import assignment_to_calendar_event
        return assignment_to_calendar_event(assignment)

    def _base(self):
        return {
            'id': 1,
            'service_type': 'Medical',
            'source_language': 'Spanish',
            'target_language': 'English',
            'location': '123 Main St',
            'city': 'Houston',
            'state': 'TX',
            'zip_code': '77001',
            'start_time': '2025-07-04T09:00:00',
            'end_time': '2025-07-04T11:00:00',
            'client': 'Houston Medical Center',
            'interpreter': 'Jane Doe',
            'interpreter_email': 'jane@example.com',
            'status': 'CONFIRMED',
            'notes': '',
            'special_requirements': 'Medical terminology required',
            'interpreter_rate': '75.00',
        }

    def test_state_drives_timezone(self):
        event = self._call(self._base())
        # TX → Central
        self.assertEqual(event['start']['timeZone'], 'America/Chicago')
        self.assertEqual(event['end']['timeZone'], 'America/Chicago')

    def test_california_timezone(self):
        data = {**self._base(), 'state': 'CA', 'city': 'Los Angeles'}
        event = self._call(data)
        self.assertEqual(event['start']['timeZone'], 'America/Los_Angeles')

    def test_unknown_state_falls_back_to_eastern(self):
        data = {**self._base(), 'state': ''}
        event = self._call(data)
        self.assertEqual(event['start']['timeZone'], 'America/New_York')

    def test_summary_format(self):
        event = self._call(self._base())
        self.assertIn('[JHBridge]', event['summary'])
        self.assertIn('Medical', event['summary'])
        self.assertIn('Spanish', event['summary'])
        self.assertIn('English', event['summary'])

    def test_location_includes_zip(self):
        event = self._call(self._base())
        self.assertIn('77001', event['location'])

    def test_interpreter_email_as_attendee(self):
        event = self._call(self._base())
        self.assertIn('attendees', event)
        self.assertEqual(event['attendees'][0]['email'], 'jane@example.com')

    def test_no_attendee_when_no_email(self):
        data = {**self._base(), 'interpreter_email': ''}
        event = self._call(data)
        self.assertNotIn('attendees', event)

    def test_description_includes_rate_and_special(self):
        event = self._call(self._base())
        desc = event['description']
        self.assertIn('$75.00/hr', desc)
        self.assertIn('Medical terminology required', desc)

    def test_two_reminders(self):
        event = self._call(self._base())
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

"""Tests for app/utils/timezone.py — state-based timezone utilities."""
from datetime import datetime

import pytz
from django.test import SimpleTestCase
from django.utils import timezone as dj_timezone
from unittest.mock import MagicMock

from app.utils.timezone import (
    STATE_TIMEZONES,
    DEFAULT_TZ_NAME,
    BOSTON_TZ,
    get_timezone_for_state,
    get_interpreter_timezone,
    format_local_datetime,
    format_datetime_for_state,
    format_datetime_for_interpreter,
    format_boston_datetime,
)


class StateTimezonesMappingTest(SimpleTestCase):
    """Verify completeness and correctness of STATE_TIMEZONES."""

    def test_all_50_states_present(self):
        all_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL',
            'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
            'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
            'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
            'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
            'WY',
        }
        missing = all_states - set(STATE_TIMEZONES.keys())
        self.assertEqual(missing, set(), f"Missing states: {missing}")

    def test_known_eastern_states(self):
        for state in ('MA', 'NY', 'FL', 'GA', 'PA', 'OH', 'MI'):
            self.assertEqual(STATE_TIMEZONES[state], 'America/New_York', state)

    def test_known_central_states(self):
        for state in ('IL', 'TX', 'MN', 'LA', 'MO'):
            self.assertEqual(STATE_TIMEZONES[state], 'America/Chicago', state)

    def test_known_mountain_states(self):
        for state in ('CO', 'MT', 'WY', 'UT'):
            self.assertEqual(STATE_TIMEZONES[state], 'America/Denver', state)

    def test_arizona_no_dst(self):
        self.assertEqual(STATE_TIMEZONES['AZ'], 'America/Phoenix')

    def test_known_pacific_states(self):
        for state in ('CA', 'WA', 'OR', 'NV'):
            self.assertEqual(STATE_TIMEZONES[state], 'America/Los_Angeles', state)

    def test_alaska_and_hawaii(self):
        self.assertEqual(STATE_TIMEZONES['AK'], 'America/Anchorage')
        self.assertEqual(STATE_TIMEZONES['HI'], 'Pacific/Honolulu')

    def test_all_tz_names_are_valid_pytz(self):
        for state, tz_name in STATE_TIMEZONES.items():
            try:
                pytz.timezone(tz_name)
            except pytz.exceptions.UnknownTimeZoneError:
                self.fail(f"Invalid timezone '{tz_name}' for state '{state}'")


class GetTimezoneForStateTest(SimpleTestCase):

    def test_known_state(self):
        tz = get_timezone_for_state('CA')
        self.assertEqual(str(tz), 'America/Los_Angeles')

    def test_case_insensitive(self):
        self.assertEqual(get_timezone_for_state('ca'), get_timezone_for_state('CA'))
        self.assertEqual(get_timezone_for_state('Ny'), get_timezone_for_state('NY'))

    def test_unknown_state_falls_back_to_eastern(self):
        tz = get_timezone_for_state('XX')
        self.assertEqual(str(tz), DEFAULT_TZ_NAME)

    def test_empty_string_falls_back(self):
        tz = get_timezone_for_state('')
        self.assertEqual(str(tz), DEFAULT_TZ_NAME)

    def test_none_falls_back(self):
        tz = get_timezone_for_state(None)
        self.assertEqual(str(tz), DEFAULT_TZ_NAME)


class GetInterpreterTimezoneTest(SimpleTestCase):

    def _make_interpreter(self, state):
        m = MagicMock()
        m.state = state
        return m

    def test_interpreter_in_california(self):
        interp = self._make_interpreter('CA')
        tz = get_interpreter_timezone(interp)
        self.assertEqual(str(tz), 'America/Los_Angeles')

    def test_interpreter_in_texas(self):
        interp = self._make_interpreter('TX')
        tz = get_interpreter_timezone(interp)
        self.assertEqual(str(tz), 'America/Chicago')

    def test_interpreter_no_state(self):
        interp = self._make_interpreter(None)
        tz = get_interpreter_timezone(interp)
        self.assertEqual(str(tz), DEFAULT_TZ_NAME)

    def test_interpreter_missing_state_attr(self):
        interp = MagicMock(spec=[])  # no 'state' attribute
        tz = get_interpreter_timezone(interp)
        self.assertEqual(str(tz), DEFAULT_TZ_NAME)


class FormatLocalDatetimeTest(SimpleTestCase):

    def _utc_dt(self, year, month, day, hour, minute):
        return dj_timezone.make_aware(
            datetime(year, month, day, hour, minute), pytz.UTC
        )

    def test_returns_empty_string_for_none(self):
        result = format_local_datetime(None, BOSTON_TZ)
        self.assertEqual(result, '')

    def test_formats_correctly_in_eastern(self):
        # 2025-07-04 14:30 UTC → 10:30 AM EDT in New York
        dt = self._utc_dt(2025, 7, 4, 14, 30)
        result = format_local_datetime(dt, BOSTON_TZ)
        self.assertIn('07/04/2025', result)
        self.assertIn('10:30 AM', result)
        self.assertIn('EDT', result)

    def test_formats_correctly_in_pacific(self):
        # 2025-07-04 14:30 UTC → 07:30 AM PDT in Los Angeles
        dt = self._utc_dt(2025, 7, 4, 14, 30)
        pac_tz = pytz.timezone('America/Los_Angeles')
        result = format_local_datetime(dt, pac_tz)
        self.assertIn('07/04/2025', result)
        self.assertIn('07:30 AM', result)
        self.assertIn('PDT', result)

    def test_format_boston_datetime_alias(self):
        dt = self._utc_dt(2025, 7, 4, 14, 30)
        self.assertEqual(format_boston_datetime(dt), format_local_datetime(dt, BOSTON_TZ))

    def test_format_boston_datetime_none(self):
        self.assertEqual(format_boston_datetime(None), '')


class FormatDatetimeConvenienceTest(SimpleTestCase):

    def _utc_dt(self):
        return dj_timezone.make_aware(datetime(2025, 1, 15, 20, 0), pytz.UTC)

    def test_format_datetime_for_state(self):
        # 2025-01-15 20:00 UTC → 15:00 EST in New York
        result = format_datetime_for_state(self._utc_dt(), 'NY')
        self.assertIn('01/15/2025', result)
        self.assertIn('03:00 PM', result)
        self.assertIn('EST', result)

    def test_format_datetime_for_interpreter(self):
        interp = MagicMock()
        interp.state = 'TX'
        # 2025-01-15 20:00 UTC → 14:00 CST in Texas
        result = format_datetime_for_interpreter(self._utc_dt(), interp)
        self.assertIn('01/15/2025', result)
        self.assertIn('02:00 PM', result)
        self.assertIn('CST', result)


class BackwardCompatibilityTest(SimpleTestCase):
    """Ensure BOSTON_TZ constant is still importable and correct."""

    def test_boston_tz_is_eastern(self):
        self.assertEqual(str(BOSTON_TZ), 'America/New_York')

"""Tests for Branch 5 serializer additions.

All tests use SimpleTestCase with MagicMock — no DB required.
"""
from datetime import datetime, timezone as dt_tz
from unittest.mock import MagicMock, PropertyMock, patch

import pytz
from django.test import SimpleTestCase

from app.api.serializers.assignments import AssignmentListSerializer, AssignmentDetailSerializer, _local_isoformat
from app.api.serializers.users import (
    InterpreterListSerializer, InterpreterDetailSerializer,
    ClientListSerializer, ClientDetailSerializer,
)
from app.api.serializers.onboarding import OnboardingDetailSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=pytz.UTC)


def _make_assignment(state='MA', has_interpreter=True):
    a = MagicMock()
    a.id = 1
    a.status = 'CONFIRMED'
    a.start_time = _utc(2025, 8, 15, 14, 0)
    a.end_time = _utc(2025, 8, 15, 16, 0)
    a.city = 'Boston'
    a.state = state
    a.interpreter_rate = '75.00'
    a.total_interpreter_payment = '150.00'
    a.is_paid = False
    a.created_at = _utc(2025, 8, 1, 9)
    a.client = None
    a.client_name = 'Test Corp'

    if has_interpreter:
        a.interpreter = MagicMock()
        a.interpreter.user.first_name = 'Jane'
        a.interpreter.user.last_name = 'Doe'
        a.interpreter.state = state
    else:
        a.interpreter = None

    # Provide minimal MagicMocks for nested serializers
    a.service_type = MagicMock()
    a.service_type.name = 'Medical'
    a.source_language = MagicMock()
    a.source_language.name = 'Spanish'
    a.source_language.code = 'ES'
    a.target_language = MagicMock()
    a.target_language.name = 'English'
    a.target_language.code = 'EN'
    return a


# ---------------------------------------------------------------------------
# _local_isoformat helper
# ---------------------------------------------------------------------------

class LocalIsoformatTest(SimpleTestCase):

    def test_none_datetime_returns_none(self):
        self.assertIsNone(_local_isoformat(None, MagicMock()))

    def test_none_interpreter_falls_back_to_boston(self):
        dt = _utc(2025, 8, 15, 14)
        result = _local_isoformat(dt, None)
        # Boston is UTC-4 (EDT) in August — 14:00 UTC → 10:00 EDT
        self.assertIsNotNone(result)
        self.assertIn('10:00', result)

    def test_california_interpreter_offset(self):
        dt = _utc(2025, 8, 15, 14)
        interp = MagicMock()
        interp.state = 'CA'
        result = _local_isoformat(dt, interp)
        # CA is PDT (UTC-7) in August — 14:00 UTC → 07:00 PDT
        self.assertIsNotNone(result)
        self.assertIn('07:00', result)

    def test_texas_interpreter_offset(self):
        dt = _utc(2025, 8, 15, 14)
        interp = MagicMock()
        interp.state = 'TX'
        result = _local_isoformat(dt, interp)
        # TX is CDT (UTC-5) in August — 14:00 UTC → 09:00 CDT
        self.assertIn('09:00', result)

    def test_returns_string(self):
        dt = _utc(2025, 1, 1, 12)
        result = _local_isoformat(dt, None)
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# AssignmentListSerializer — start_time_local / end_time_local
# ---------------------------------------------------------------------------

class AssignmentListSerializerLocalTimeTest(SimpleTestCase):

    def _serialize(self, assignment):
        s = AssignmentListSerializer(assignment)
        return s.data

    def test_has_start_time_local_field(self):
        a = _make_assignment()
        data = self._serialize(a)
        self.assertIn('start_time_local', data)

    def test_has_end_time_local_field(self):
        a = _make_assignment()
        data = self._serialize(a)
        self.assertIn('end_time_local', data)

    def test_start_time_local_is_string(self):
        a = _make_assignment()
        data = self._serialize(a)
        self.assertIsInstance(data['start_time_local'], str)

    def test_start_time_local_none_when_no_start(self):
        a = _make_assignment()
        a.start_time = None
        data = self._serialize(a)
        self.assertIsNone(data['start_time_local'])

    def test_start_time_local_differs_from_utc_for_ca(self):
        a = _make_assignment(state='CA')
        data = self._serialize(a)
        # UTC is e.g. 2025-08-15T14:00:00+00:00
        # CA local is e.g. 2025-08-15T07:00:00-07:00
        self.assertNotEqual(data['start_time_local'], data['start_time'])

    def test_no_interpreter_uses_boston_tz(self):
        a = _make_assignment(has_interpreter=False)
        data = self._serialize(a)
        self.assertIsNotNone(data['start_time_local'])


# ---------------------------------------------------------------------------
# AssignmentDetailSerializer — start_time_local / end_time_local
# ---------------------------------------------------------------------------

class AssignmentDetailSerializerLocalTimeTest(SimpleTestCase):

    def _serialize(self, assignment):
        s = AssignmentDetailSerializer(assignment)
        return s.data

    def test_has_local_time_fields(self):
        a = _make_assignment()
        # Need additional fields for Detail serializer
        a.quote = None
        a.location = '123 Main St'
        a.zip_code = '02101'
        a.is_paid = False
        a.minimum_hours = 2
        a.notes = ''
        a.special_requirements = ''
        a.updated_at = _utc(2025, 8, 1, 10)
        a.completed_at = None
        a.client_email = None
        a.client_phone = None

        data = self._serialize(a)
        self.assertIn('start_time_local', data)
        self.assertIn('end_time_local', data)


# ---------------------------------------------------------------------------
# InterpreterListSerializer — is_on_mission, lat, lng
# ---------------------------------------------------------------------------

class InterpreterListSerializerTest(SimpleTestCase):

    def _make_interpreter(self, has_location=True, is_on_mission=False):
        interp = MagicMock()
        interp.id = 1
        interp.city = 'Boston'
        interp.state = 'MA'
        interp.hourly_rate = '75.00'
        interp.active = True
        interp.has_accepted_contract = True
        interp.is_dashboard_enabled = True
        interp.is_manually_blocked = False
        interp.user.email = 'jane@example.com'
        interp.user.first_name = 'Jane'
        interp.user.last_name = 'Doe'
        interp.user.phone = '617-555-0001'

        if has_location:
            loc = MagicMock()
            loc.is_on_mission = is_on_mission
            loc.latitude = 42.3601
            loc.longitude = -71.0589
            interp.locations.first.return_value = loc
        else:
            interp.locations.first.return_value = None

        interp.languages.all.return_value = []
        # missions_count and avg_rating come from annotation
        interp.missions_count = 5
        interp.avg_rating = 4.5
        return interp

    def test_has_is_on_mission(self):
        interp = self._make_interpreter()
        data = InterpreterListSerializer(interp).data
        self.assertIn('is_on_mission', data)

    def test_has_lat_lng(self):
        interp = self._make_interpreter()
        data = InterpreterListSerializer(interp).data
        self.assertIn('lat', data)
        self.assertIn('lng', data)

    def test_is_on_mission_true(self):
        interp = self._make_interpreter(is_on_mission=True)
        data = InterpreterListSerializer(interp).data
        self.assertTrue(data['is_on_mission'])

    def test_is_on_mission_false(self):
        interp = self._make_interpreter(is_on_mission=False)
        data = InterpreterListSerializer(interp).data
        self.assertFalse(data['is_on_mission'])

    def test_is_on_mission_false_when_no_location(self):
        interp = self._make_interpreter(has_location=False)
        data = InterpreterListSerializer(interp).data
        self.assertFalse(data['is_on_mission'])

    def test_lat_lng_none_when_no_location(self):
        interp = self._make_interpreter(has_location=False)
        data = InterpreterListSerializer(interp).data
        self.assertIsNone(data['lat'])
        self.assertIsNone(data['lng'])

    def test_lat_lng_present_when_location_exists(self):
        interp = self._make_interpreter()
        data = InterpreterListSerializer(interp).data
        self.assertAlmostEqual(data['lat'], 42.3601, places=3)
        self.assertAlmostEqual(data['lng'], -71.0589, places=3)

    def test_setup_eager_loading_prefetches_locations(self):
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.prefetch_related.return_value = qs
        qs.annotate.return_value = qs
        InterpreterListSerializer.setup_eager_loading(qs)
        # Verify 'locations' appears in one of the prefetch_related calls
        all_calls = str(qs.prefetch_related.call_args_list)
        self.assertIn('locations', all_calls)


# ---------------------------------------------------------------------------
# ClientListSerializer — mission_count, total_revenue, last_mission_date
# ---------------------------------------------------------------------------

class ClientListSerializerTest(SimpleTestCase):

    def _make_client(self):
        c = MagicMock()
        c.id = 1
        c.company_name = 'Boston Medical'
        c.city = 'Boston'
        c.state = 'MA'
        c.phone = '617-555-0002'
        c.active = True
        c.user.email = 'bmc@example.com'
        c.user.first_name = 'Bob'
        c.user.last_name = 'Smith'
        c.preferred_language = None
        return c

    @patch('app.api.serializers.users.Assignment')
    @patch('app.api.serializers.users.Invoice')
    def test_has_mission_count(self, MockInvoice, MockAssignment):
        MockAssignment.objects.filter.return_value.count.return_value = 7
        MockInvoice.objects.filter.return_value.aggregate.return_value = {'total': None}
        MockAssignment.objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = None

        data = ClientListSerializer(self._make_client()).data
        self.assertIn('mission_count', data)
        self.assertEqual(data['mission_count'], 7)

    @patch('app.api.serializers.users.Assignment')
    @patch('app.api.serializers.users.Invoice')
    def test_total_revenue_sum(self, MockInvoice, MockAssignment):
        MockAssignment.objects.filter.return_value.count.return_value = 0
        MockInvoice.objects.filter.return_value.aggregate.return_value = {'total': 5000}
        MockAssignment.objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = None

        data = ClientListSerializer(self._make_client()).data
        self.assertEqual(data['total_revenue'], 5000)

    @patch('app.api.serializers.users.Assignment')
    @patch('app.api.serializers.users.Invoice')
    def test_total_revenue_zero_when_no_invoices(self, MockInvoice, MockAssignment):
        MockAssignment.objects.filter.return_value.count.return_value = 0
        MockInvoice.objects.filter.return_value.aggregate.return_value = {'total': None}
        MockAssignment.objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = None

        data = ClientListSerializer(self._make_client()).data
        self.assertEqual(data['total_revenue'], 0)

    @patch('app.api.serializers.users.Assignment')
    @patch('app.api.serializers.users.Invoice')
    def test_last_mission_date_none_when_no_assignments(self, MockInvoice, MockAssignment):
        MockAssignment.objects.filter.return_value.count.return_value = 0
        MockInvoice.objects.filter.return_value.aggregate.return_value = {'total': None}
        MockAssignment.objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = None

        data = ClientListSerializer(self._make_client()).data
        self.assertIsNone(data['last_mission_date'])

    @patch('app.api.serializers.users.Assignment')
    @patch('app.api.serializers.users.Invoice')
    def test_last_mission_date_isoformat(self, MockInvoice, MockAssignment):
        dt = _utc(2025, 7, 4, 9)
        MockAssignment.objects.filter.return_value.count.return_value = 1
        MockInvoice.objects.filter.return_value.aggregate.return_value = {'total': None}
        MockAssignment.objects.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = dt

        data = ClientListSerializer(self._make_client()).data
        self.assertIsNotNone(data['last_mission_date'])
        self.assertIn('2025-07-04', data['last_mission_date'])


# ---------------------------------------------------------------------------
# OnboardingDetailSerializer — languages
# ---------------------------------------------------------------------------

class OnboardingDetailSerializerLanguagesTest(SimpleTestCase):

    def _make_invitation(self, has_interpreter=True):
        inv = MagicMock()
        inv.id = 1
        inv.invitation_number = 'INV-2026-00001'
        inv.email = 'jane@example.com'
        inv.first_name = 'Jane'
        inv.last_name = 'Doe'
        inv.full_name = 'Jane Doe'
        inv.phone = '617-555-0001'
        inv.current_phase = 'INVITED'
        inv.version = 1
        inv.token = 'abc123'
        inv.created_at = _utc(2026, 1, 1, 9)
        inv.email_sent_at = _utc(2026, 1, 1, 9)
        inv.email_opened_at = None
        inv.welcome_viewed_at = None
        inv.account_created_at = None
        inv.profile_completed_at = None
        inv.contract_started_at = None
        inv.completed_at = None
        inv.voided_at = None
        inv.expires_at = _utc(2026, 2, 1, 9)
        inv.user = None
        inv.created_by = None
        inv.voided_by = None
        inv.void_reason = ''
        inv.contract_invitation = None
        inv.tracking_events.all.return_value = []
        inv.is_expired.return_value = False

        if has_interpreter:
            inv.interpreter = MagicMock()
            inv.interpreter.id = 5
            inv.interpreter.languages.values_list.return_value = ['Spanish', 'French']
        else:
            inv.interpreter = None

        return inv

    def test_languages_field_present(self):
        inv = self._make_invitation()
        data = OnboardingDetailSerializer(inv).data
        self.assertIn('languages', data)

    def test_languages_returns_list(self):
        inv = self._make_invitation()
        data = OnboardingDetailSerializer(inv).data
        self.assertIsInstance(data['languages'], list)

    def test_languages_populated_from_interpreter(self):
        inv = self._make_invitation()
        data = OnboardingDetailSerializer(inv).data
        self.assertIn('Spanish', data['languages'])
        self.assertIn('French', data['languages'])

    def test_languages_empty_when_no_interpreter(self):
        inv = self._make_invitation(has_interpreter=False)
        data = OnboardingDetailSerializer(inv).data
        self.assertEqual(data['languages'], [])

    def test_setup_eager_loading_prefetches_interpreter_languages(self):
        qs = MagicMock()
        qs.select_related.return_value = qs
        qs.prefetch_related.return_value = qs
        OnboardingDetailSerializer.setup_eager_loading(qs)
        all_calls = str(qs.prefetch_related.call_args_list)
        self.assertIn('interpreter__languages', all_calls)

"""Tests for app/services/onboarding_service.py."""
from datetime import timedelta
from unittest.mock import MagicMock, patch, call

from django.test import SimpleTestCase
from django.utils import timezone as dj_tz

import app.services.onboarding_service as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_invitation(phase='INVITED', version=1):
    inv = MagicMock()
    inv.id = 10
    inv.invitation_number = 'INV-2026-00001'
    inv.email = 'jane@example.com'
    inv.first_name = 'Jane'
    inv.last_name = 'Doe'
    inv.phone = '617-555-0001'
    inv.current_phase = phase
    inv.version = version
    inv.email_sent_at = None
    inv.expires_at = dj_tz.now() + timedelta(days=30)
    return inv


# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------

class PhaseConstantsTest(SimpleTestCase):

    def test_phase_order_length(self):
        self.assertEqual(len(svc.PHASE_ORDER), 7)

    def test_phase_order_first_last(self):
        self.assertEqual(svc.PHASE_ORDER[0], 'INVITED')
        self.assertEqual(svc.PHASE_ORDER[-1], 'COMPLETED')

    def test_phase_timestamps_covers_all_but_invited(self):
        # Every phase except INVITED has a timestamp field
        for phase in svc.PHASE_ORDER[1:]:
            self.assertIn(phase, svc.PHASE_TIMESTAMPS)

    def test_phase_template_map_all_active_phases(self):
        active = ['INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED',
                  'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED']
        for phase in active:
            self.assertIn(phase, svc.PHASE_TEMPLATE_MAP)

    def test_phase_template_map_correct_values(self):
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['INVITED'], 'RESEND_ISSUE')
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['EMAIL_OPENED'], 'STUCK_OPENED')
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['WELCOME_VIEWED'], 'STUCK_WELCOME')
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['ACCOUNT_CREATED'], 'STUCK_ACCOUNT')
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['PROFILE_COMPLETED'], 'STUCK_ACCOUNT')
        self.assertEqual(svc.PHASE_TEMPLATE_MAP['CONTRACT_STARTED'], 'STUCK_CONTRACT')


# ---------------------------------------------------------------------------
# advance_invitation
# ---------------------------------------------------------------------------

class AdvanceInvitationTest(SimpleTestCase):

    def test_invited_advances_to_email_opened(self):
        inv = _make_invitation('INVITED')
        result = svc.advance_invitation(inv)
        self.assertEqual(inv.current_phase, 'EMAIL_OPENED')
        self.assertIsNotNone(inv.email_opened_at)
        self.assertIs(result, inv)

    def test_email_opened_advances_to_welcome_viewed(self):
        inv = _make_invitation('EMAIL_OPENED')
        svc.advance_invitation(inv)
        self.assertEqual(inv.current_phase, 'WELCOME_VIEWED')
        self.assertIsNotNone(inv.welcome_viewed_at)

    def test_contract_started_advances_to_completed(self):
        inv = _make_invitation('CONTRACT_STARTED')
        svc.advance_invitation(inv)
        self.assertEqual(inv.current_phase, 'COMPLETED')
        self.assertIsNotNone(inv.completed_at)

    def test_completed_raises_value_error(self):
        inv = _make_invitation('COMPLETED')
        with self.assertRaises(ValueError):
            svc.advance_invitation(inv)

    def test_voided_raises_value_error(self):
        inv = _make_invitation('VOIDED')
        with self.assertRaises(ValueError):
            svc.advance_invitation(inv)

    def test_expired_raises_value_error(self):
        inv = _make_invitation('EXPIRED')
        with self.assertRaises(ValueError):
            svc.advance_invitation(inv)

    def test_save_is_called(self):
        inv = _make_invitation('INVITED')
        svc.advance_invitation(inv)
        inv.save.assert_called_once()

    def test_invited_has_no_timestamp_field(self):
        """INVITED is the initial phase — no timestamp needed when advancing from it."""
        inv = _make_invitation('INVITED')
        svc.advance_invitation(inv)
        # setattr was called on EMAIL_OPENED's timestamp field, not on INVITED's
        self.assertNotIn('invited_at', svc.PHASE_TIMESTAMPS)


# ---------------------------------------------------------------------------
# extend_invitation
# ---------------------------------------------------------------------------

class ExtendInvitationTest(SimpleTestCase):

    def test_default_14_days(self):
        inv = _make_invitation()
        before = dj_tz.now()
        svc.extend_invitation(inv)
        # expires_at should be ~14 days from now
        self.assertIsNotNone(inv.expires_at)
        inv.save.assert_called_once_with(update_fields=['expires_at'])

    def test_custom_days(self):
        inv = _make_invitation()
        svc.extend_invitation(inv, days=30)
        inv.save.assert_called_once_with(update_fields=['expires_at'])

    def test_returns_invitation(self):
        inv = _make_invitation()
        result = svc.extend_invitation(inv)
        self.assertIs(result, inv)


# ---------------------------------------------------------------------------
# void_invitation
# ---------------------------------------------------------------------------

class VoidInvitationTest(SimpleTestCase):

    def test_void_active_invitation(self):
        inv = _make_invitation('INVITED')
        MockEventModel = MagicMock()

        with patch.dict('sys.modules', {
            'app.models': MagicMock(OnboardingTrackingEvent=MockEventModel),
        }):
            svc.void_invitation(inv, voided_by=MagicMock(), reason='test reason')

        self.assertEqual(inv.current_phase, 'VOIDED')
        self.assertIsNotNone(inv.voided_at)
        self.assertEqual(inv.void_reason, 'test reason')
        inv.save.assert_called_once()
        MockEventModel.objects.create.assert_called_once()

    def test_void_completed_raises(self):
        inv = _make_invitation('COMPLETED')
        with self.assertRaises(ValueError) as ctx:
            svc.void_invitation(inv, voided_by=MagicMock())
        self.assertIn('COMPLETED', str(ctx.exception))

    def test_void_voided_raises(self):
        inv = _make_invitation('VOIDED')
        with self.assertRaises(ValueError):
            svc.void_invitation(inv, voided_by=MagicMock())


# ---------------------------------------------------------------------------
# resend_invitation — key behaviour: voids old + creates new
# ---------------------------------------------------------------------------

class ResendInvitationTest(SimpleTestCase):

    def _run_resend(self, old_phase='INVITED', template_type=None):
        """Helper: run resend_invitation with fully mocked DB layer."""
        old_inv = _make_invitation(old_phase, version=2)
        new_inv = _make_invitation('INVITED', version=3)
        new_inv.email_sent_at = None

        creator = MagicMock()

        MockInvitationModel = MagicMock()
        MockInvitationModel.objects.create.return_value = new_inv

        MockEventModel = MagicMock()

        MockEmailService = MagicMock()
        MockEmailService.send_invitation_email.return_value = True

        with patch.dict('sys.modules', {
            'app.models': MagicMock(
                OnboardingInvitation=MockInvitationModel,
                OnboardingTrackingEvent=MockEventModel,
            ),
            'app.services.email_service': MagicMock(
                OnboardingEmailService=MockEmailService,
            ),
        }):
            result = svc.resend_invitation(old_inv, creator, template_type=template_type)

        return old_inv, new_inv, result, MockInvitationModel, MockEventModel, MockEmailService

    def test_old_invitation_voided(self):
        old_inv, *_ = self._run_resend('INVITED')
        self.assertEqual(old_inv.current_phase, 'VOIDED')

    def test_new_invitation_created_with_incremented_version(self):
        old_inv, _, result, MockInvModel, *_ = self._run_resend('INVITED')
        call_kwargs = MockInvModel.objects.create.call_args[1]
        self.assertEqual(call_kwargs['version'], old_inv.version + 1)

    def test_new_invitation_same_email(self):
        old_inv, _, result, MockInvModel, *_ = self._run_resend()
        call_kwargs = MockInvModel.objects.create.call_args[1]
        self.assertEqual(call_kwargs['email'], old_inv.email)

    def test_resent_tracking_event_created(self):
        _, new_inv, _, _, MockEventModel, _ = self._run_resend()
        MockEventModel.objects.create.assert_called_once()
        create_kwargs = MockEventModel.objects.create.call_args[1]
        self.assertEqual(create_kwargs['event_type'], 'RESENT')

    def test_tracking_event_includes_original_id(self):
        old_inv, _, _, _, MockEventModel, _ = self._run_resend()
        create_kwargs = MockEventModel.objects.create.call_args[1]
        self.assertEqual(
            create_kwargs['metadata']['original_invitation_id'],
            str(old_inv.id),
        )

    def test_email_sent_via_service(self):
        _, new_inv, _, _, _, MockEmailSvc = self._run_resend(template_type='STUCK_CONTRACT')
        MockEmailSvc.send_invitation_email.assert_called_once()
        _, kwargs = MockEmailSvc.send_invitation_email.call_args
        self.assertEqual(kwargs.get('template_type'), 'STUCK_CONTRACT')

    def test_already_voided_not_voided_again(self):
        """If old invitation is already VOIDED, skip the void step."""
        old_inv, *_ = self._run_resend('VOIDED')
        # Phase stays VOIDED (was already VOIDED before the call)
        self.assertEqual(old_inv.current_phase, 'VOIDED')
        # save() on old invitation should NOT have been called for voiding
        old_inv.save.assert_not_called()

    def test_returns_new_invitation(self):
        _, new_inv, result, *_ = self._run_resend()
        self.assertIs(result, new_inv)


# ---------------------------------------------------------------------------
# create_invitation — key behaviour: creates, links user, sends email
# ---------------------------------------------------------------------------

class CreateInvitationTest(SimpleTestCase):

    def _run_create(self, existing_user=None, email_sent=True):
        invitation = _make_invitation()
        invitation.email_sent_at = None
        creator = MagicMock()

        MockInvModel = MagicMock()
        MockInvModel.objects.create.return_value = invitation

        MockUserModel = MagicMock()
        MockUserModel.objects.filter.return_value.first.return_value = existing_user

        MockEventModel = MagicMock()

        MockEmailSvc = MagicMock()
        MockEmailSvc.send_invitation_email.return_value = email_sent

        with patch.dict('sys.modules', {
            'app.models': MagicMock(
                OnboardingInvitation=MockInvModel,
                OnboardingTrackingEvent=MockEventModel,
                User=MockUserModel,
            ),
            'app.services.email_service': MagicMock(
                OnboardingEmailService=MockEmailSvc,
            ),
        }):
            result = svc.create_invitation(
                first_name='Jane',
                last_name='Doe',
                email='jane@example.com',
                phone='617-555-0001',
                created_by=creator,
            )

        return result, invitation, MockInvModel, MockEventModel, MockEmailSvc

    def test_invitation_created(self):
        _, _, MockInvModel, *_ = self._run_create()
        MockInvModel.objects.create.assert_called_once()

    def test_email_sent(self):
        _, _, _, _, MockEmailSvc = self._run_create()
        MockEmailSvc.send_invitation_email.assert_called_once()

    def test_email_sent_tracking_event_created(self):
        _, _, _, MockEventModel, _ = self._run_create(email_sent=True)
        create_kwargs = MockEventModel.objects.create.call_args[1]
        self.assertEqual(create_kwargs['event_type'], 'EMAIL_SENT')

    def test_no_tracking_event_when_email_fails(self):
        _, _, _, MockEventModel, _ = self._run_create(email_sent=False)
        MockEventModel.objects.create.assert_not_called()

    def test_links_existing_user(self):
        existing = MagicMock()
        existing.interpreter = MagicMock()
        _, invitation, *_ = self._run_create(existing_user=existing)
        self.assertEqual(invitation.user, existing)
        self.assertEqual(invitation.interpreter, existing.interpreter)

    def test_returns_invitation(self):
        result, invitation, *_ = self._run_create()
        self.assertIs(result, invitation)

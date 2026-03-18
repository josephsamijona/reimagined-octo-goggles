from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from app.models import OnboardingInvitation, OnboardingTrackingEvent
from app.admin.onboarding import OnboardingInvitationAdmin
from django.contrib.admin.sites import AdminSite
from unittest.mock import patch

class OnboardingResendTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = OnboardingInvitationAdmin(OnboardingInvitation, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        
        self.invitation = OnboardingInvitation.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            created_by=self.user
        )

    @patch('app.services.email_service.OnboardingEmailService.send_invitation_email')
    def test_resend_issue_email(self, mock_send_email):
        request = self.factory.get('/')
        request.user = self.user
        queryset = OnboardingInvitation.objects.filter(id=self.invitation.id)
        
        self.admin.resend_issue_email(request, queryset)
        
        # Verify old invitation is voided
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.current_phase, 'VOIDED')
        self.assertEqual(self.invitation.void_reason, "Resent due to reported issue")
        
        # Verify new invitation is created
        new_inv = OnboardingInvitation.objects.latest('created_at')
        self.assertNotEqual(new_inv.id, self.invitation.id)
        self.assertEqual(new_inv.version, self.invitation.version + 1)
        self.assertEqual(new_inv.email, self.invitation.email)
        
        # Verify email call
        mock_send_email.assert_called_once_with(new_inv, request, template_type='RESEND_ISSUE')
        
        # Verify tracking event
        event = OnboardingTrackingEvent.objects.filter(invitation=new_inv, event_type='RESENT').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata['template_type'], 'RESEND_ISSUE')

    @patch('app.services.email_service.OnboardingEmailService.send_invitation_email')
    def test_resend_stuck_welcome_email(self, mock_send_email):
        request = self.factory.get('/')
        request.user = self.user
        queryset = OnboardingInvitation.objects.filter(id=self.invitation.id)
        
        self.admin.resend_stuck_welcome_email(request, queryset)
        
        new_inv = OnboardingInvitation.objects.latest('created_at')
        mock_send_email.assert_called_once_with(new_inv, request, template_type='STUCK_WELCOME')

    @patch('app.services.email_service.OnboardingEmailService.send_invitation_email')
    def test_resend_standard_email(self, mock_send_email):
        request = self.factory.get('/')
        request.user = self.user
        queryset = OnboardingInvitation.objects.filter(id=self.invitation.id)
        
        self.admin.resend_invitations(request, queryset)
        
        new_inv = OnboardingInvitation.objects.latest('created_at')
        mock_send_email.assert_called_once_with(new_inv, request, template_type=None)

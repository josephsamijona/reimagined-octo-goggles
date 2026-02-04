from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from app.models import ContractInvitation, Interpreter, User
import uuid

class ContractInvitationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testinterpreter', email='test@example.com', password='password')
        self.interpreter = Interpreter.objects.create(user=self.user)
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')

    def test_invitation_creation_and_tokens(self):
        """Test that tokens and invitation number are generated on save."""
        invitation = ContractInvitation.objects.create(
            interpreter=self.interpreter,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        self.assertIsNotNone(invitation.token)
        self.assertIsNotNone(invitation.accept_token)
        self.assertIsNotNone(invitation.review_token)
        self.assertTrue(invitation.invitation_number.startswith('INV-2026-'))
        self.assertEqual(invitation.status, 'SENT')

    def test_is_expired(self):
        """Test the is_expired method."""
        # Future expiration
        invitation = ContractInvitation.objects.create(
            interpreter=self.interpreter,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=1)
        )
        self.assertFalse(invitation.is_expired())
        
        # Past expiration
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save()
        self.assertTrue(invitation.is_expired())

    def test_status_transitions(self):
        """Test status changes."""
        invitation = ContractInvitation.objects.create(
            interpreter=self.interpreter,
            created_by=self.admin_user
        )
        
        invitation.status = 'OPENED'
        invitation.save()
        self.assertEqual(ContractInvitation.objects.get(id=invitation.id).status, 'OPENED')
        
        invitation.status = 'SIGNED'
        invitation.save()
        self.assertEqual(ContractInvitation.objects.get(id=invitation.id).status, 'SIGNED')

    def test_unique_tokens(self):
        """Test that tokens are unique between invitations."""
        inv1 = ContractInvitation.objects.create(interpreter=self.interpreter, created_by=self.admin_user)
        inv2 = ContractInvitation.objects.create(interpreter=self.interpreter, created_by=self.admin_user)
        
        self.assertNotEqual(inv1.token, inv2.token)
        self.assertNotEqual(inv1.accept_token, inv2.accept_token)
        self.assertNotEqual(inv1.review_token, inv2.review_token)

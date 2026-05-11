from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from app.models import LoginAttempt, MFADevice, User
from shared.constants import ROLE_ADMIN, ROLE_CLIENT


@override_settings(
    GOOGLE_OAUTH_CLIENT_ID="test-google-client-id",
    CELERY_BROKER_URL="memory://",
    CELERY_RESULT_BACKEND="cache+memory://",
)
class GoogleAuthAPITests(APITestCase):
    endpoint = "/api/v1/auth/google/"

    @staticmethod
    def _create_user(email, role=ROLE_ADMIN, is_active=True):
        username = email.split("@")[0]
        return User.objects.create_user(
            username=username,
            email=email,
            password="TestPassword123!",
            role=role,
            is_active=is_active,
        )

    def test_missing_id_token_returns_400(self):
        response = self.client.post(self.endpoint, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_token", response.data["detail"].lower())

    @patch("app.api.viewsets.auth.google_id_token.verify_oauth2_token")
    def test_invalid_google_token_returns_401(self, mock_verify):
        mock_verify.side_effect = ValueError("bad token")
        response = self.client.post(self.endpoint, {"id_token": "invalid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Invalid Google token.")

    @patch("app.api.viewsets.auth.google_id_token.verify_oauth2_token")
    def test_non_admin_email_is_rejected(self, mock_verify):
        self._create_user("staff@example.com", role=ROLE_CLIENT, is_active=True)
        mock_verify.return_value = {
            "email": "staff@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("No admin account", response.data["detail"])

    @patch("app.api.viewsets.auth.google_id_token.verify_oauth2_token")
    def test_admin_without_mfa_gets_mfa_setup_required(self, mock_verify):
        user = self._create_user("admin-no-mfa@example.com", role=ROLE_ADMIN, is_active=True)
        mock_verify.return_value = {
            "email": user.email,
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], user.email)
        self.assertFalse(response.data["mfa_required"])
        self.assertTrue(response.data["mfa_setup_required"])

    @patch("app.api.viewsets.auth.google_id_token.verify_oauth2_token")
    def test_admin_with_mfa_gets_mfa_required(self, mock_verify):
        user = self._create_user("admin-mfa@example.com", role=ROLE_ADMIN, is_active=True)
        MFADevice.objects.create(user=user, secret="A" * 32, is_verified=True)
        mock_verify.return_value = {
            "email": user.email,
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        response = self.client.post(self.endpoint, {"id_token": "valid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["mfa_required"])
        self.assertFalse(response.data["mfa_setup_required"])

    @patch("app.api.viewsets.auth.google_id_token.verify_oauth2_token")
    def test_locked_out_email_returns_429(self, mock_verify):
        email = "locked-admin@example.com"
        self._create_user(email, role=ROLE_ADMIN, is_active=True)
        mock_verify.return_value = {
            "email": email,
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        for _ in range(LoginAttempt.MAX_ATTEMPTS):
            LoginAttempt.record_attempt(email, "127.0.0.1", False, "invalid_credentials")

        response = self.client.post(self.endpoint, {"id_token": "valid"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

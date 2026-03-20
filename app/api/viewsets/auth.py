"""
Authentication API views: login, MFA, WebAuthn, device trust, logout.
All endpoints are prefixed with /api/v1/auth/ (set in app/api/urls.py).
"""
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from app.api.services.auth_service import (
    AuthService,
    MFAService,
    WebAuthnService,
    DeviceTrustService,
    get_tokens_for_user,
    get_client_ip,
    user_payload,
)
from app.models import User
from app.models.auth_security import MFADevice

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════════════════════

class LoginView(APIView):
    """
    POST /auth/login/
    Accepts email + password, returns JWT tokens.
    If MFA is enabled, returns a partial token with mfa_required=true.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        print(f"[LOGIN VIEW] ===== LOGIN REQUEST =====")
        print(f"[LOGIN VIEW] Content-Type: {request.content_type}")
        print(f"[LOGIN VIEW] request.data type: {type(request.data)}")
        print(f"[LOGIN VIEW] request.data keys: {list(request.data.keys()) if hasattr(request.data, 'keys') else 'N/A'}")
        print(f"[LOGIN VIEW] request.data: {dict(request.data)}")
        identifier = request.data.get("identifier", "") or request.data.get("email", "")
        password = request.data.get("password", "")
        print(f"[LOGIN VIEW] Resolved identifier={identifier!r}, has_password={bool(password)}")

        result = AuthService.login(request, identifier, password)
        print(f"[LOGIN VIEW] Result: success={result.get('success')}, status={result.get('status', 200)}, error={result.get('error', 'none')}")

        if not result["success"]:
            return Response(
                {"detail": result["error"]},
                status=result["status"],
            )

        response_data = {
            "access": result["tokens"]["access"],
            "refresh": result["tokens"]["refresh"],
            "user": result["user"],
            "mfa_required": result.get("mfa_required", False),
            "mfa_setup_required": result.get("mfa_setup_required", False),
        }

        return Response(response_data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════
#  MFA
# ═══════════════════════════════════════════════════════════════════

class MFASetupView(APIView):
    """
    POST /auth/mfa/setup/
    Generate a TOTP secret + QR code for first-time MFA setup.
    Requires a valid (partial) JWT token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = MFAService.setup(request.user)
        return Response(result, status=status.HTTP_200_OK)


class MFAVerifyView(APIView):
    """
    POST /auth/mfa/verify/
    Verify a TOTP code and upgrade the partial JWT to a full token.
    Body: { "code": "123456" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip()

        if not code:
            return Response(
                {"detail": "Verification code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if MFAService.verify(request.user, code):
            # Issue full token
            tokens = get_tokens_for_user(
                request.user, mfa_verified=True, auth_method="password+mfa"
            )
            return Response({
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": user_payload(request.user),
                "mfa_verified": True,
            })

        return Response(
            {"detail": "Invalid verification code."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class MFABackupCodesView(APIView):
    """
    POST /auth/mfa/backup-codes/
    Generate a new set of backup codes (invalidates previous ones).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        codes = MFAService.generate_backup_codes(request.user)
        return Response({
            "backup_codes": codes,
            "warning": "Save these codes securely. They cannot be shown again.",
        })


# ═══════════════════════════════════════════════════════════════════
#  WEBAUTHN
# ═══════════════════════════════════════════════════════════════════

class WebAuthnRegisterOptionsView(APIView):
    """
    POST /auth/webauthn/register/options/
    Generate WebAuthn registration challenge.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            options, state = WebAuthnService.get_registration_options(request.user)
            # Store state in session for verification
            request.session["webauthn_register_state"] = state
            return Response(options)
        except Exception as e:
            logger.error(f"WebAuthn register options error: {e}")
            return Response(
                {"detail": "Failed to generate registration options."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WebAuthnRegisterVerifyView(APIView):
    """
    POST /auth/webauthn/register/verify/
    Verify WebAuthn registration and store the credential.
    Body: { "response": {...}, "device_name": "My MacBook" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        state = request.session.get("webauthn_register_state")
        if not state:
            return Response(
                {"detail": "No registration in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = request.data.get("response", {})
        device_name = request.data.get("device_name", "Unknown Device")

        try:
            WebAuthnService.verify_registration(
                request.user, state, response_data, device_name
            )
            del request.session["webauthn_register_state"]
            return Response({"detail": "WebAuthn credential registered successfully."})
        except Exception as e:
            logger.error(f"WebAuthn register verify error: {e}")
            return Response(
                {"detail": "Registration verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WebAuthnLoginOptionsView(APIView):
    """
    POST /auth/webauthn/login/options/
    Generate WebAuthn login challenge.
    Body: { "email": "admin@jhbridge.com" }
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email", "")
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        options, state, user = WebAuthnService.get_login_options(email)
        if not options:
            return Response(
                {"detail": "No WebAuthn credentials found for this email."},
                status=status.HTTP_404_NOT_FOUND,
            )

        request.session["webauthn_login_state"] = state
        request.session["webauthn_login_user_id"] = user.id
        return Response(options)


class WebAuthnLoginVerifyView(APIView):
    """
    POST /auth/webauthn/login/verify/
    Verify WebAuthn assertion and return full JWT token.
    Body: { "response": {...} }
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        state = request.session.get("webauthn_login_state")
        user_id = request.session.get("webauthn_login_user_id")

        if not state or not user_id:
            return Response(
                {"detail": "No login challenge in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = request.data.get("response", {})

        try:
            WebAuthnService.verify_login(state, response_data, user)
            # Clean up session
            del request.session["webauthn_login_state"]
            del request.session["webauthn_login_user_id"]

            # WebAuthn bypasses MFA — issue full token
            tokens = get_tokens_for_user(
                user, mfa_verified=True, auth_method="webauthn"
            )
            # Update last login IP
            ip = get_client_ip(request)
            User.objects.filter(pk=user.pk).update(last_login_ip=ip)

            return Response({
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": user_payload(user),
                "mfa_verified": True,
            })
        except Exception as e:
            logger.error(f"WebAuthn login verify error: {e}")
            return Response(
                {"detail": "WebAuthn authentication failed."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ═══════════════════════════════════════════════════════════════════
#  DEVICE TRUST
# ═══════════════════════════════════════════════════════════════════

class DeviceTrustView(APIView):
    """
    POST /auth/device/trust/
    Issue a 30-day trust token for this device.
    Body: { "fingerprint": "browser-fingerprint-hash" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fingerprint = request.data.get("fingerprint", "")
        if not fingerprint:
            return Response(
                {"detail": "Device fingerprint is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = DeviceTrustService.issue_token(
            request.user, fingerprint, request
        )
        return Response({
            "trust_token": token,
            "expires_in_days": DeviceTrustService.TRUST_DURATION_DAYS,
        })


# ═══════════════════════════════════════════════════════════════════
#  LOGOUT
# ═══════════════════════════════════════════════════════════════════

class LogoutView(APIView):
    """
    POST /auth/logout/
    Blacklist the refresh token.
    Body: { "refresh": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh", "")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logged out successfully."})
        except Exception:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ═══════════════════════════════════════════════════════════════════
#  ME (existing, kept for compatibility)
# ═══════════════════════════════════════════════════════════════════

class MeView(APIView):
    """GET /auth/me/ — Returns the currently authenticated user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = user_payload(user)
        data.update({
            "phone": user.phone,
            "registration_complete": user.registration_complete,
            "is_dashboard_enabled": user.is_dashboard_enabled,
            "created_at": user.created_at,
            "has_mfa": MFADevice.objects.filter(user=user, is_verified=True).exists(),
            "has_webauthn": user.webauthn_credentials.exists(),
        })

        # Role-specific profile
        if user.role == "CLIENT" and hasattr(user, "client_profile"):
            client = user.client_profile
            data["profile"] = {
                "id": client.id,
                "company_name": client.company_name,
                "city": client.city,
                "state": client.state,
                "active": client.active,
            }
        elif user.role == "INTERPRETER" and hasattr(user, "interpreter_profile"):
            interp = user.interpreter_profile
            data["profile"] = {
                "id": interp.id,
                "city": interp.city,
                "state": interp.state,
                "active": interp.active,
                "is_manually_blocked": interp.is_manually_blocked,
                "has_accepted_contract": interp.has_accepted_contract,
            }

        return Response(data)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """POST /auth/token/refresh/ — Wraps SimpleJWT TokenRefreshView."""
    pass

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
    StepUpAuthService,
    DeviceTrustService,
    get_tokens_for_user,
    get_client_ip,
    user_payload,
)
from app.models import User
from app.models.auth_security import MFADevice, WebAuthnCredential

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
#  STEP-UP AUTH (re-verify identity before sensitive operations)
#  Uses signed tokens — no session/cookie dependency.
# ═══════════════════════════════════════════════════════════════════

class StepUpAuthView(APIView):
    """
    POST /auth/step-up/
    Re-verify identity via password or TOTP before sensitive operations.
    Body: { "method": "password"|"totp", "password": "...", "code": "..." }
    Returns: { "verified": true, "step_up_token": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        method = request.data.get("method", "")
        if method not in ("password", "totp"):
            return Response(
                {"detail": "Method must be 'password' or 'totp'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, result = StepUpAuthService.verify(
            request.user,
            method,
            password=request.data.get("password", ""),
            code=request.data.get("code", ""),
        )

        if not success:
            return Response(
                {"detail": result},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "detail": "Identity verified.",
            "verified": True,
            "step_up_token": result,
        })


class StepUpAuthStatusView(APIView):
    """
    GET /auth/step-up/status/
    Return available verification methods for this user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        has_mfa = MFADevice.objects.filter(user=request.user, is_verified=True).exists()
        has_passkeys = WebAuthnCredential.objects.filter(user=request.user).exists()

        methods = ["password"]
        if has_mfa:
            methods.append("totp")
        if has_passkeys:
            methods.append("passkey")

        return Response({"methods": methods})


class StepUpPasskeyOptionsView(APIView):
    """
    POST /auth/step-up/passkey/options/
    Generate WebAuthn assertion challenge for step-up auth via existing passkey.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        credentials = []
        for cred in WebAuthnCredential.objects.filter(user=request.user):
            credentials.append(WebAuthnService._decode_credential(cred))

        if not credentials:
            return Response(
                {"detail": "No passkeys registered."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from app.api.services.auth_service import fido2_server
        auth_data, state = fido2_server.authenticate_begin(credentials)
        request.session["step_up_passkey_state"] = state
        return Response(auth_data)


class StepUpPasskeyVerifyView(APIView):
    """
    POST /auth/step-up/passkey/verify/
    Verify WebAuthn assertion for step-up auth.
    Body: { "response": {...} }
    Returns: { "verified": true, "step_up_token": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        state = request.session.get("step_up_passkey_state")
        if not state:
            return Response(
                {"detail": "No passkey challenge in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = request.data.get("response", {})
        try:
            WebAuthnService.verify_login(state, response_data, request.user)
            del request.session["step_up_passkey_state"]
            # Issue step-up token
            success, token = StepUpAuthService.verify(request.user, "passkey")
            return Response({
                "detail": "Identity verified.",
                "verified": True,
                "step_up_token": token,
            })
        except Exception as e:
            logger.error(f"Step-up passkey verify error: {e}")
            return Response(
                {"detail": "Passkey verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ═══════════════════════════════════════════════════════════════════
#  WEBAUTHN
# ═══════════════════════════════════════════════════════════════════

class WebAuthnRegisterOptionsView(APIView):
    """
    POST /auth/webauthn/register/options/
    Generate WebAuthn registration challenge.
    Requires step-up token in X-Step-Up-Token header.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.META.get("HTTP_X_STEP_UP_TOKEN", "")
        if not StepUpAuthService.validate_token(token, request.user):
            return Response(
                {"detail": "Step-up authentication required.", "step_up_required": True},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            options, state = WebAuthnService.get_registration_options(request.user)
            # Store state in session for verification step
            request.session["webauthn_register_state"] = state
            logger.info(f"WebAuthn register options generated for {request.user.email}")
            return Response(options)
        except Exception as e:
            logger.error(f"WebAuthn register options error: {e}", exc_info=True)
            return Response(
                {"detail": f"Failed to generate registration options: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WebAuthnRegisterVerifyView(APIView):
    """
    POST /auth/webauthn/register/verify/
    Verify WebAuthn registration and store the credential.
    Body: { "response": {...}, "device_name": "My MacBook" }
    Requires step-up token in X-Step-Up-Token header.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.META.get("HTTP_X_STEP_UP_TOKEN", "")
        if not StepUpAuthService.validate_token(token, request.user):
            return Response(
                {"detail": "Step-up authentication required.", "step_up_required": True},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            logger.info(f"WebAuthn credential registered for {request.user.email}: {device_name}")
            return Response({"detail": "WebAuthn credential registered successfully."})
        except Exception as e:
            logger.error(f"WebAuthn register verify error: {e}", exc_info=True)
            return Response(
                {"detail": f"Registration verification failed: {e}"},
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
                {"detail": "Email or username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            options, state, user = WebAuthnService.get_login_options(email)
        except Exception as e:
            logger.error(f"WebAuthn login options error: {e}", exc_info=True)
            return Response(
                {"detail": f"Failed to generate login options: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not options:
            return Response(
                {"detail": "No WebAuthn credentials found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        request.session["webauthn_login_state"] = state
        request.session["webauthn_login_user_id"] = user.id
        return Response(options)


class WebAuthnListView(APIView):
    """GET /auth/webauthn/credentials/ — List user's registered passkeys."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        creds = WebAuthnCredential.objects.filter(user=request.user).order_by('-created_at')
        return Response([{
            "id": str(c.id),
            "device_name": c.device_name,
            "created_at": c.created_at,
            "last_used": c.last_used,
        } for c in creds])


class WebAuthnDeleteView(APIView):
    """DELETE /auth/webauthn/credentials/<id>/ — Remove a passkey."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, credential_id):
        deleted, _ = WebAuthnCredential.objects.filter(
            id=credential_id, user=request.user
        ).delete()
        if not deleted:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"detail": "Credential deleted."})


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

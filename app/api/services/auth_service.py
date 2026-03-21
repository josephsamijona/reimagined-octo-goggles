"""
Authentication services: login flow, MFA, WebAuthn, and device trust.
"""
import base64
import hashlib
import io
import logging
import secrets
from datetime import timedelta

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    AttestedCredentialData,
    AuthenticatorData,
)
from fido2 import cbor
from rest_framework_simplejwt.tokens import RefreshToken

from app.models import User
from app.models.auth_security import (
    MFADevice,
    MFABackupCode,
    WebAuthnCredential,
    TrustedDevice,
    LoginAttempt,
)
from app.models.security import AuditLog

logger = logging.getLogger(__name__)

# ─── FIDO2 Server Configuration ─────────────────────────────────────
RP_ID = "localhost"  # Change in production to your domain
RP_NAME = "JHBridge Command Center"

rp = PublicKeyCredentialRpEntity(name=RP_NAME, id=RP_ID)
fido2_server = Fido2Server(rp)


# ─── Helper: get client IP ──────────────────────────────────────────
def get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


# ─── Custom JWT with MFA claim ──────────────────────────────────────
def get_tokens_for_user(user, mfa_verified=False, auth_method="password"):
    """Generate JWT tokens with custom claims for MFA status."""
    refresh = RefreshToken.for_user(user)
    refresh["mfa_verified"] = mfa_verified
    refresh["auth_method"] = auth_method
    refresh["role"] = user.role

    access = refresh.access_token
    access["mfa_verified"] = mfa_verified
    access["auth_method"] = auth_method
    access["role"] = user.role

    return {
        "access": str(access),
        "refresh": str(refresh),
    }


def user_payload(user):
    """Standard user data for API responses."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
    }


# ═══════════════════════════════════════════════════════════════════
#  AUTH SERVICE
# ═══════════════════════════════════════════════════════════════════

class AuthService:
    """Handles email+password login and brute-force protection."""

    @staticmethod
    def login(request, email: str, password: str):
        """
        Validate credentials. Returns:
        - On success: dict with tokens + user + mfa status
        - On failure: dict with error details
        """
        print(f"[AUTH_SERVICE] login() called with email param={email!r}")
        identifier = email.strip().lower()
        print(f"[AUTH_SERVICE] identifier={identifier!r} after strip/lower")
        ip = get_client_ip(request)

        # Check lockout
        if LoginAttempt.is_locked_out(identifier):
            return {
                "success": False,
                "error": "Account temporarily locked due to too many failed attempts. Try again in 15 minutes.",
                "status": 429,
            }

        if not identifier or not password:
            print(f"[AUTH_SERVICE] EMPTY: identifier={identifier!r}, password={'(empty)' if not password else '(set)'}")
            return {
                "success": False,
                "error": "Email/username and password are required.",
                "status": 400,
            }

        # Try authenticating by username first, then by email
        print(f"[AUTH_SERVICE] Trying authenticate(username={identifier!r}) ...")
        user = authenticate(request, username=identifier, password=password)
        print(f"[AUTH_SERVICE] authenticate by username result: {user}")
        if user is None:
            # Try to find user by email and authenticate with their username
            try:
                user_by_email = User.objects.get(email=identifier)
                print(f"[AUTH_SERVICE] Found user by email: {user_by_email.username}")
                user = authenticate(request, username=user_by_email.username, password=password)
                print(f"[AUTH_SERVICE] authenticate by email->username result: {user}")
            except User.DoesNotExist:
                print(f"[AUTH_SERVICE] No user found with email={identifier!r}")

        if user is None:
            LoginAttempt.record_attempt(identifier, ip, False, "invalid_credentials")
            return {
                "success": False,
                "error": "Invalid credentials.",
                "status": 401,
            }

        if not user.is_active:
            LoginAttempt.record_attempt(identifier, ip, False, "account_disabled")
            return {
                "success": False,
                "error": "Account is disabled.",
                "status": 403,
            }

        # Record successful attempt
        LoginAttempt.record_attempt(identifier, ip, True)
        User.objects.filter(pk=user.pk).update(last_login_ip=ip)

        # Check if MFA is set up
        has_mfa = MFADevice.objects.filter(user=user, is_verified=True).exists()

        if has_mfa:
            # Return partial token (mfa_verified=False)
            tokens = get_tokens_for_user(user, mfa_verified=False)
            return {
                "success": True,
                "mfa_required": True,
                "tokens": tokens,
                "user": user_payload(user),
            }
        else:
            # No MFA set up — admin must set up MFA on first login
            if user.role == "ADMIN":
                tokens = get_tokens_for_user(user, mfa_verified=False)
                return {
                    "success": True,
                    "mfa_setup_required": True,
                    "tokens": tokens,
                    "user": user_payload(user),
                }
            # Non-admin users get full access without MFA (for now)
            tokens = get_tokens_for_user(user, mfa_verified=True)
            return {
                "success": True,
                "mfa_required": False,
                "tokens": tokens,
                "user": user_payload(user),
            }


# ═══════════════════════════════════════════════════════════════════
#  MFA SERVICE
# ═══════════════════════════════════════════════════════════════════

class MFAService:
    """Handles TOTP-based MFA setup and verification."""

    @staticmethod
    def setup(user):
        """Generate a new TOTP secret and return the provisioning URI + QR code."""
        secret = pyotp.random_base32()

        device, created = MFADevice.objects.update_or_create(
            user=user,
            defaults={"secret": secret, "is_verified": False},
        )

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="JHBridge Admin",
        )

        # Generate QR code as base64
        img = qrcode.make(provisioning_uri)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": f"data:image/png;base64,{qr_base64}",
        }

    @staticmethod
    def verify(user, code: str):
        """Verify a TOTP code. Returns True if valid."""
        try:
            device = MFADevice.objects.get(user=user)
        except MFADevice.DoesNotExist:
            return False

        totp = pyotp.TOTP(device.secret)

        if totp.verify(code, valid_window=1):
            # Mark device as verified if this is the first successful verification
            if not device.is_verified:
                device.is_verified = True
                device.save(update_fields=["is_verified"])
            return True

        # Check backup codes
        return MFAService.verify_backup_code(user, code)

    @staticmethod
    def verify_backup_code(user, code: str) -> bool:
        """Try to use a backup code."""
        code_hash = MFABackupCode.hash_code(code.upper().strip())
        backup = MFABackupCode.objects.filter(
            user=user, code_hash=code_hash, used=False
        ).first()

        if backup:
            backup.used = True
            backup.used_at = timezone.now()
            backup.save(update_fields=["used", "used_at"])
            return True
        return False

    @staticmethod
    def generate_backup_codes(user):
        """Generate a fresh set of backup codes."""
        return MFABackupCode.generate_codes(user, count=10)


# ═══════════════════════════════════════════════════════════════════
#  WEBAUTHN SERVICE
# ═══════════════════════════════════════════════════════════════════

class WebAuthnService:
    """Handles FIDO2/WebAuthn registration and authentication."""

    @staticmethod
    def _decode_credential(cred):
        """Decode a stored WebAuthnCredential back to AttestedCredentialData."""
        raw = base64.b64decode(cred.public_key_b64)
        # Try CBOR-decode first (legacy format: cbor.encode was used on the bytes)
        try:
            decoded = cbor.decode(raw)
            if isinstance(decoded, bytes):
                return AttestedCredentialData(decoded)
        except Exception:
            pass
        # Direct bytes format (new format: raw AttestedCredentialData bytes)
        return AttestedCredentialData(raw)

    @staticmethod
    def get_registration_options(user):
        """Generate WebAuthn registration challenge."""
        existing_credentials = []
        for cred in WebAuthnCredential.objects.filter(user=user):
            existing_credentials.append(WebAuthnService._decode_credential(cred))

        user_entity = PublicKeyCredentialUserEntity(
            id=str(user.id).encode(),
            name=user.email,
            display_name=f"{user.first_name} {user.last_name}",
        )

        registration_data, state = fido2_server.register_begin(
            user=user_entity,
            credentials=existing_credentials,
        )

        return registration_data, state

    @staticmethod
    def verify_registration(user, state, response, device_name="Unknown Device"):
        """Verify the WebAuthn registration response and store the credential."""
        auth_data = fido2_server.register_complete(state, response)

        cred = auth_data.credential_data
        WebAuthnCredential.objects.create(
            user=user,
            credential_id_b64=base64.b64encode(cred.credential_id).decode(),
            public_key_b64=base64.b64encode(bytes(cred)).decode(),
            sign_count=0,
            device_name=device_name,
        )

        return True

    @staticmethod
    def get_login_options(identifier: str):
        """Generate WebAuthn login challenge for a user (accepts email or username)."""
        identifier = identifier.strip().lower()
        try:
            user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                return None, None, None

        credentials = []
        for cred in WebAuthnCredential.objects.filter(user=user):
            credentials.append(WebAuthnService._decode_credential(cred))

        if not credentials:
            return None, None, None

        auth_data, state = fido2_server.authenticate_begin(credentials)
        return auth_data, state, user

    @staticmethod
    def verify_login(state, response, user):
        """Verify the WebAuthn login response."""
        credentials = []
        for cred in WebAuthnCredential.objects.filter(user=user):
            credentials.append(WebAuthnService._decode_credential(cred))

        result = fido2_server.authenticate_complete(
            state, credentials, response
        )

        # fido2 v2: result is AuthenticatorData with .counter for sign count
        # Update last_used on all user credentials (credential ID matching
        # is complex in v2, and users typically have few credentials)
        WebAuthnCredential.objects.filter(user=user).update(
            sign_count=getattr(result, "counter", 0),
            last_used=timezone.now(),
        )

        return True


# ═══════════════════════════════════════════════════════════════════
#  STEP-UP AUTH SERVICE
# ═══════════════════════════════════════════════════════════════════

STEP_UP_TTL_SECONDS = 300  # 5 minutes


class StepUpAuthService:
    """
    Re-verify identity before sensitive operations (e.g. registering a passkey).
    Supports password, TOTP code, or existing passkey assertion.
    Issues a signed token (no session dependency).
    """

    @staticmethod
    def verify(user, method, **kwargs):
        """
        Verify identity. Returns (success: bool, error_or_token: str).
        On success, returns a signed step-up token.
        method: 'password' | 'totp' | 'passkey'
        """
        if method == "password":
            password = kwargs.get("password", "")
            if not password:
                return False, "Password is required."
            from django.contrib.auth import authenticate as django_authenticate
            authed = django_authenticate(username=user.username, password=password)
            if authed is None:
                return False, "Invalid password."

        elif method == "totp":
            code = kwargs.get("code", "")
            if not code:
                return False, "TOTP code is required."
            if not MFAService.verify(user, code):
                return False, "Invalid verification code."

        elif method == "passkey":
            # Already verified by the caller (view layer handles the ceremony)
            pass

        else:
            return False, f"Unknown verification method: {method}"

        # Issue a signed step-up token
        token = StepUpAuthService._issue_token(user)
        return True, token

    @staticmethod
    def _issue_token(user):
        """Create a short-lived signed step-up token using Django's signer."""
        from django.core.signing import TimestampSigner
        signer = TimestampSigner(salt="step-up-auth")
        return signer.sign(str(user.pk))

    @staticmethod
    def validate_token(token, user):
        """Validate a step-up token. Returns True if valid and belongs to user."""
        if not token:
            return False
        from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
        signer = TimestampSigner(salt="step-up-auth")
        try:
            value = signer.unsign(token, max_age=STEP_UP_TTL_SECONDS)
            return str(value) == str(user.pk)
        except (SignatureExpired, BadSignature):
            return False


# ═══════════════════════════════════════════════════════════════════
#  DEVICE TRUST SERVICE
# ═══════════════════════════════════════════════════════════════════

class DeviceTrustService:
    """Handles 'Trust this device' functionality."""

    TRUST_DURATION_DAYS = 30

    @staticmethod
    def issue_token(user, fingerprint: str, request=None) -> str:
        """Create a trust token for this device. Returns the plaintext token."""
        token = secrets.token_urlsafe(48)
        token_hash = TrustedDevice.hash_token(token)

        ip = get_client_ip(request) if request else None
        user_agent = request.META.get("HTTP_USER_AGENT", "") if request else ""

        TrustedDevice.objects.create(
            user=user,
            device_fingerprint=hashlib.sha256(fingerprint.encode()).hexdigest(),
            token_hash=token_hash,
            ip_address=ip,
            user_agent=user_agent,
            expires_at=timezone.now() + timedelta(days=DeviceTrustService.TRUST_DURATION_DAYS),
        )

        return token

    @staticmethod
    def validate_token(token: str):
        """Validate a trust token. Returns the user if valid, None otherwise."""
        token_hash = TrustedDevice.hash_token(token)
        try:
            device = TrustedDevice.objects.select_related("user").get(
                token_hash=token_hash
            )
        except TrustedDevice.DoesNotExist:
            return None

        if not device.is_valid:
            device.delete()
            return None

        return device.user

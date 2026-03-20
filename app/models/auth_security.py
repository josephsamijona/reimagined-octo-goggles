"""
Authentication & Security models for MFA, WebAuthn, Device Trust, and Brute-force protection.
"""
import hashlib
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class MFADevice(models.Model):
    """
    Stores TOTP secret for each user.
    The secret is base32-encoded and used with Google Authenticator / Authy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_device'
    )
    secret = models.CharField(max_length=64, help_text="Base32-encoded TOTP secret")
    is_verified = models.BooleanField(
        default=False,
        help_text="True once the user has confirmed their first TOTP code"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_mfa_device'
        verbose_name = 'MFA Device'
        verbose_name_plural = 'MFA Devices'

    def __str__(self):
        status = "verified" if self.is_verified else "pending"
        return f"MFA ({status}) - {self.user.email}"


class MFABackupCode(models.Model):
    """
    One-time backup codes for MFA recovery.
    Codes are stored as SHA-256 hashes for security.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_backup_codes'
    )
    code_hash = models.CharField(max_length=64, help_text="SHA-256 hash of the backup code")
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_mfa_backup_code'
        verbose_name = 'MFA Backup Code'

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def generate_codes(cls, user, count=10):
        """Generate a set of one-time backup codes and return the plaintext list."""
        # Delete existing unused codes
        cls.objects.filter(user=user, used=False).delete()

        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8-char hex code, e.g. "A3F2E1B7"
            cls.objects.create(user=user, code_hash=cls.hash_code(code))
            codes.append(code)
        return codes


class WebAuthnCredential(models.Model):
    """
    Stores FIDO2/WebAuthn credentials (passkeys, YubiKeys, biometrics).
    Credential data is stored as base64-encoded strings for MySQL compatibility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webauthn_credentials'
    )
    credential_id_b64 = models.CharField(
        max_length=512, unique=True,
        help_text="Base64-encoded FIDO2 credential ID"
    )
    public_key_b64 = models.TextField(help_text="Base64-encoded CBOR public key")
    sign_count = models.PositiveIntegerField(default=0)
    device_name = models.CharField(max_length=100, default="Unknown Device")
    
    # Transports (usb, ble, nfc, internal)
    transports = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'app_webauthn_credential'
        verbose_name = 'WebAuthn Credential'
        verbose_name_plural = 'WebAuthn Credentials'

    def __str__(self):
        return f"WebAuthn: {self.device_name} - {self.user.email}"


class TrustedDevice(models.Model):
    """
    'Trust this device' tokens. Valid for 30 days.
    Allows WebAuthn-only login without password+MFA.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trusted_devices'
    )
    device_fingerprint = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of browser fingerprint data"
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 hash of the trust token sent to the client"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_trusted_device'
        verbose_name = 'Trusted Device'
        verbose_name_plural = 'Trusted Devices'

    def __str__(self):
        return f"Trusted device for {self.user.email} (expires {self.expires_at})"

    @property
    def is_valid(self):
        return timezone.now() < self.expires_at

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class LoginAttempt(models.Model):
    """
    Tracks login attempts for brute-force protection.
    After MAX_ATTEMPTS failures in LOCKOUT_WINDOW, the account is locked for LOCKOUT_DURATION.
    """
    MAX_ATTEMPTS = 5
    LOCKOUT_WINDOW = timezone.timedelta(minutes=15)
    LOCKOUT_DURATION = timezone.timedelta(minutes=15)

    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=50, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_login_attempt'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]

    @classmethod
    def is_locked_out(cls, email: str) -> bool:
        """Check if the email is currently locked out due to too many failed attempts."""
        cutoff = timezone.now() - cls.LOCKOUT_WINDOW
        recent_failures = cls.objects.filter(
            email=email.lower(),
            success=False,
            timestamp__gte=cutoff
        ).count()
        return recent_failures >= cls.MAX_ATTEMPTS

    @classmethod
    def record_attempt(cls, email: str, ip: str, success: bool, reason: str = ""):
        cls.objects.create(
            email=email.lower(),
            ip_address=ip,
            success=success,
            failure_reason=reason,
        )

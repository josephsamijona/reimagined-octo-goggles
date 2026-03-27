"""
Admin MFA views: email OTP (default), TOTP setup, WebAuthn, settings, passkey management.
Includes brute-force protection, input validation, and comprehensive audit logging.
"""
import json
import logging
import random
import re
import string
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from app.api.services.auth_service import (
    MFAService,
    WebAuthnService,
    get_client_ip,
)
from app.models.auth_security import MFADevice, MFABackupCode, WebAuthnCredential
from app.models.security import AuditLog

logger = logging.getLogger(__name__)

staff_required = [login_required, staff_member_required]

# ─── Constants ───────────────────────────────────────────────────────
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6
CODE_PATTERN = re.compile(r'^[0-9A-Za-z]{6,8}$')


# ─── Helpers ─────────────────────────────────────────────────────────

def _audit(user, action, request, details=None):
    """Log a security event to AuditLog."""
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name='AdminMFA',
        object_id=str(user.pk),
        changes=details or {},
        ip_address=get_client_ip(request),
    )


def _get_attempt_key(request, prefix='mfa'):
    """Session key for brute-force tracking."""
    return f'_admin_{prefix}_attempts'


def _get_lockout_key(request, prefix='mfa'):
    """Session key for lockout timestamp."""
    return f'_admin_{prefix}_lockout_until'


def _is_locked_out(request, prefix='mfa'):
    """Check if user is currently locked out."""
    lockout_until = request.session.get(_get_lockout_key(request, prefix))
    if lockout_until:
        if timezone.now().isoformat() < lockout_until:
            return True
        # Lockout expired — clear
        request.session.pop(_get_lockout_key(request, prefix), None)
        request.session.pop(_get_attempt_key(request, prefix), None)
    return False


def _record_failed_attempt(request, prefix='mfa'):
    """Record a failed attempt. Returns (is_now_locked, attempts_remaining)."""
    key = _get_attempt_key(request, prefix)
    attempts = request.session.get(key, 0) + 1
    request.session[key] = attempts

    if attempts >= MAX_ATTEMPTS:
        lockout = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
        request.session[_get_lockout_key(request, prefix)] = lockout.isoformat()
        _audit(request.user, f'LOCKOUT_{prefix.upper()}', request, {
            'attempts': attempts,
            'lockout_minutes': LOCKOUT_MINUTES,
        })
        return True, 0

    return False, MAX_ATTEMPTS - attempts


def _clear_attempts(request, prefix='mfa'):
    """Clear attempt counter on success."""
    request.session.pop(_get_attempt_key(request, prefix), None)
    request.session.pop(_get_lockout_key(request, prefix), None)


def _validate_code(code):
    """Validate OTP/TOTP code format. Returns (clean_code, error_msg)."""
    if not code:
        return None, 'Please enter your verification code.'
    code = code.strip()
    if len(code) < 6 or len(code) > 8:
        return None, 'Code must be 6 to 8 characters.'
    if not CODE_PATTERN.match(code):
        return None, 'Code must contain only letters and numbers.'
    return code, None


def _generate_email_otp():
    """Generate a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))


def _send_otp_email(user, otp):
    """Send OTP code via email."""
    send_mail(
        subject='JHBridge Admin — Your verification code',
        message=(
            f'Hello {user.first_name or user.username},\n\n'
            f'Your admin verification code is: {otp}\n\n'
            f'This code expires in {OTP_EXPIRY_MINUTES} minutes.\n'
            f'If you did not request this, please ignore this email.\n\n'
            f'— JHBridge Security'
        ),
        from_email='JHBridge Security <security@jhbridgetranslation.com>',
        recipient_list=[user.email],
        fail_silently=False,
    )


def _lockout_error():
    return f'Too many failed attempts. Please wait {LOCKOUT_MINUTES} minutes before trying again.'


# ─── EMAIL OTP (default for users without MFA) ──────────────────────

@method_decorator(staff_required, name='dispatch')
class EmailOTPView(View):
    """Send a one-time code by email for users who haven't setup MFA yet."""

    def get(self, request):
        if request.session.get('admin_mfa_verified'):
            return redirect(reverse('admin:index'))

        # Auto-send OTP on page load (if not already sent recently)
        last_sent = request.session.get('_email_otp_sent_at')
        now = timezone.now()
        if not last_sent or now.isoformat() > (
            (timezone.datetime.fromisoformat(last_sent) + timedelta(seconds=60)).isoformat()
        ):
            otp = _generate_email_otp()
            request.session['_email_otp_code'] = otp
            request.session['_email_otp_expires'] = (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
            request.session['_email_otp_sent_at'] = now.isoformat()
            try:
                _send_otp_email(request.user, otp)
                _audit(request.user, 'EMAIL_OTP_SENT', request)
            except Exception as e:
                logger.exception("Failed to send OTP email")

        masked_email = _mask_email(request.user.email)
        return render(request, 'admin/mfa/email_otp.html', {
            'masked_email': masked_email,
            'title': 'Email Verification',
        })

    def post(self, request):
        masked_email = _mask_email(request.user.email)

        # Lockout check
        if _is_locked_out(request, 'email_otp'):
            return render(request, 'admin/mfa/email_otp.html', {
                'masked_email': masked_email,
                'error': _lockout_error(),
                'locked': True,
                'title': 'Email Verification',
            })

        action = request.POST.get('action', 'verify')

        # Resend OTP
        if action == 'resend':
            otp = _generate_email_otp()
            request.session['_email_otp_code'] = otp
            request.session['_email_otp_expires'] = (
                timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
            ).isoformat()
            request.session['_email_otp_sent_at'] = timezone.now().isoformat()
            try:
                _send_otp_email(request.user, otp)
                _audit(request.user, 'EMAIL_OTP_RESENT', request)
            except Exception:
                pass
            return render(request, 'admin/mfa/email_otp.html', {
                'masked_email': masked_email,
                'success': 'A new code has been sent to your email.',
                'title': 'Email Verification',
            })

        # Verify OTP
        raw_code = request.POST.get('code', '')
        code, validation_error = _validate_code(raw_code)
        if validation_error:
            return render(request, 'admin/mfa/email_otp.html', {
                'masked_email': masked_email,
                'error': validation_error,
                'title': 'Email Verification',
            })

        stored_otp = request.session.get('_email_otp_code')
        expires = request.session.get('_email_otp_expires')

        # Check expiry
        if not stored_otp or not expires or timezone.now().isoformat() > expires:
            return render(request, 'admin/mfa/email_otp.html', {
                'masked_email': masked_email,
                'error': 'Code has expired. Please request a new one.',
                'title': 'Email Verification',
            })

        if code == stored_otp:
            _clear_attempts(request, 'email_otp')
            request.session['admin_mfa_verified'] = True
            for k in ['_email_otp_code', '_email_otp_expires', '_email_otp_sent_at']:
                request.session.pop(k, None)
            _audit(request.user, 'MFA_VERIFY_EMAIL_OTP', request)
            # Redirect to MFA setup prompt (not directly to admin)
            return redirect(reverse('admin_mfa:setup_prompt'))

        # Failed
        locked, remaining = _record_failed_attempt(request, 'email_otp')
        _audit(request.user, 'MFA_FAIL_EMAIL_OTP', request, {'remaining': remaining})
        if locked:
            error = _lockout_error()
        else:
            error = f'Invalid code. {remaining} attempt(s) remaining.'

        return render(request, 'admin/mfa/email_otp.html', {
            'masked_email': masked_email,
            'error': error,
            'locked': locked,
            'title': 'Email Verification',
        })


def _mask_email(email):
    """Mask email: d****e@g****.com"""
    local, domain = email.split('@')
    domain_parts = domain.split('.')
    masked_local = local[0] + '****' + local[-1] if len(local) > 1 else local[0] + '****'
    masked_domain = domain_parts[0][0] + '****' + '.' + '.'.join(domain_parts[1:])
    return f'{masked_local}@{masked_domain}'


# ─── SETUP PROMPT (shown after email OTP, before admin access) ───────

@method_decorator(staff_required, name='dispatch')
class SetupPromptView(View):
    """Suggest MFA setup after email OTP verification. User can skip."""

    def get(self, request):
        # If user already has MFA, go to admin
        has_mfa = MFADevice.objects.filter(user=request.user, is_verified=True).exists()
        has_webauthn = WebAuthnCredential.objects.filter(user=request.user).exists()
        if has_mfa or has_webauthn:
            return redirect(reverse('admin:index'))

        return render(request, 'admin/mfa/setup_prompt.html', {
            'title': 'Secure Your Account',
        })

    def post(self, request):
        action = request.POST.get('action', 'skip')
        if action == 'setup':
            return redirect(reverse('admin_mfa:setup'))
        # Skip — go to admin
        _audit(request.user, 'MFA_SETUP_SKIPPED', request)
        return redirect(reverse('admin:index'))


# ─── SETUP ───────────────────────────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class MFASetupView(View):
    """TOTP/WebAuthn setup page."""

    def get(self, request):
        if MFADevice.objects.filter(user=request.user, is_verified=True).exists():
            return redirect(reverse('admin_mfa:settings'))

        setup_data = MFAService.setup(request.user)
        return render(request, 'admin/mfa/setup.html', {
            'qr_code': setup_data['qr_code'],
            'secret': setup_data['secret'],
            'title': 'MFA Setup',
        })

    def post(self, request):
        if _is_locked_out(request, 'mfa_setup'):
            setup_data = MFAService.setup(request.user)
            return render(request, 'admin/mfa/setup.html', {
                'qr_code': setup_data['qr_code'],
                'secret': setup_data['secret'],
                'error': _lockout_error(),
                'locked': True,
                'title': 'MFA Setup',
            })

        raw_code = request.POST.get('code', '')
        code, validation_error = _validate_code(raw_code)

        if validation_error:
            setup_data = MFAService.setup(request.user)
            return render(request, 'admin/mfa/setup.html', {
                'qr_code': setup_data['qr_code'],
                'secret': setup_data['secret'],
                'error': validation_error,
                'title': 'MFA Setup',
            })

        if MFAService.verify(request.user, code):
            _clear_attempts(request, 'mfa_setup')
            backup_codes = MFAService.generate_backup_codes(request.user)
            request.session['admin_mfa_verified'] = True
            _audit(request.user, 'MFA_SETUP_TOTP', request)
            return render(request, 'admin/mfa/backup_codes.html', {
                'backup_codes': backup_codes,
                'title': 'Backup Codes',
            })

        locked, remaining = _record_failed_attempt(request, 'mfa_setup')
        _audit(request.user, 'MFA_FAIL_SETUP', request, {'remaining': remaining})

        # Re-read device for QR display
        device = MFADevice.objects.filter(user=request.user).first()
        qr_b64 = ''
        if device:
            import pyotp, qrcode, io, base64
            totp = pyotp.TOTP(device.secret)
            uri = totp.provisioning_uri(name=request.user.email, issuer_name="JHBridge Admin")
            img = qrcode.make(uri)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

        error = _lockout_error() if locked else f'Invalid code. {remaining} attempt(s) remaining.'
        return render(request, 'admin/mfa/setup.html', {
            'qr_code': qr_b64,
            'secret': device.secret if device else '',
            'error': error,
            'locked': locked,
            'title': 'MFA Setup',
        })


# ─── VERIFY ──────────────────────────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class MFAVerifyView(View):
    """MFA verification: TOTP code, backup code, or WebAuthn."""

    def get(self, request):
        if request.session.get('admin_mfa_verified'):
            return redirect(reverse('admin:index'))

        has_webauthn = WebAuthnCredential.objects.filter(user=request.user).exists()
        return render(request, 'admin/mfa/verify.html', {
            'has_webauthn': has_webauthn,
            'title': 'MFA Verification',
        })

    def post(self, request):
        has_webauthn = WebAuthnCredential.objects.filter(user=request.user).exists()

        if _is_locked_out(request, 'mfa_verify'):
            return render(request, 'admin/mfa/verify.html', {
                'has_webauthn': has_webauthn,
                'error': _lockout_error(),
                'locked': True,
                'title': 'MFA Verification',
            })

        raw_code = request.POST.get('code', '')
        code, validation_error = _validate_code(raw_code)
        if validation_error:
            return render(request, 'admin/mfa/verify.html', {
                'has_webauthn': has_webauthn,
                'error': validation_error,
                'title': 'MFA Verification',
            })

        if MFAService.verify(request.user, code):
            _clear_attempts(request, 'mfa_verify')
            request.session['admin_mfa_verified'] = True
            _audit(request.user, 'MFA_VERIFY_TOTP', request)
            return redirect(reverse('admin:index'))

        locked, remaining = _record_failed_attempt(request, 'mfa_verify')
        _audit(request.user, 'MFA_FAIL_VERIFY', request, {'remaining': remaining})

        error = _lockout_error() if locked else f'Invalid code. {remaining} attempt(s) remaining.'
        return render(request, 'admin/mfa/verify.html', {
            'has_webauthn': has_webauthn,
            'error': error,
            'locked': locked,
            'title': 'MFA Verification',
        })


# ─── WEBAUTHN ENDPOINTS (JSON) ──────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class WebAuthnRegisterBeginView(View):
    def post(self, request):
        try:
            registration_data, state = WebAuthnService.get_registration_options(request.user)
            request.session['webauthn_register_state'] = state
            return JsonResponse({
                'publicKey': _serialize_registration(registration_data),
            })
        except Exception as e:
            logger.exception("WebAuthn register begin error")
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_required, name='dispatch')
class WebAuthnRegisterCompleteView(View):
    def post(self, request):
        try:
            state = request.session.pop('webauthn_register_state', None)
            if not state:
                return JsonResponse({'error': 'No registration in progress.'}, status=400)

            body = json.loads(request.body)
            device_name = body.get('device_name', 'Admin Device')
            # Validate device name
            if not device_name or len(device_name) > 100:
                device_name = 'Admin Device'
            device_name = re.sub(r'[<>&\'"\\]', '', device_name)[:100]

            response = body.get('credential')
            WebAuthnService.verify_registration(request.user, state, response, device_name)

            if not MFADevice.objects.filter(user=request.user, is_verified=True).exists():
                request.session['admin_mfa_verified'] = True

            _audit(request.user, 'WEBAUTHN_REGISTER', request, {'device_name': device_name})
            return JsonResponse({'ok': True})
        except Exception as e:
            logger.exception("WebAuthn register complete error")
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(staff_required, name='dispatch')
class WebAuthnLoginBeginView(View):
    def post(self, request):
        try:
            auth_data, state, user = WebAuthnService.get_login_options(request.user.email)
            if not auth_data:
                return JsonResponse({'error': 'No passkeys registered.'}, status=400)

            request.session['webauthn_login_state'] = state
            return JsonResponse({
                'publicKey': _serialize_authentication(auth_data),
            })
        except Exception as e:
            logger.exception("WebAuthn login begin error")
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_required, name='dispatch')
class WebAuthnLoginCompleteView(View):
    def post(self, request):
        try:
            state = request.session.pop('webauthn_login_state', None)
            if not state:
                return JsonResponse({'error': 'No login in progress.'}, status=400)

            body = json.loads(request.body)
            response = body.get('credential')

            WebAuthnService.verify_login(state, response, request.user)
            request.session['admin_mfa_verified'] = True
            request.session['admin_reauth_verified'] = True
            _audit(request.user, 'MFA_VERIFY_WEBAUTHN', request)
            return JsonResponse({'ok': True})
        except Exception as e:
            _audit(request.user, 'MFA_FAIL_WEBAUTHN', request, {'error': str(e)})
            logger.exception("WebAuthn login complete error")
            return JsonResponse({'error': str(e)}, status=400)


# ─── SETTINGS ────────────────────────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class MFASettingsView(View):
    def get(self, request):
        if not request.session.get('admin_mfa_verified'):
            return redirect(reverse('admin_mfa:verify'))

        passkeys = WebAuthnCredential.objects.filter(user=request.user).order_by('-created_at')
        has_totp = MFADevice.objects.filter(user=request.user, is_verified=True).exists()
        backup_count = MFABackupCode.objects.filter(user=request.user, used=False).count()

        return render(request, 'admin/mfa/settings.html', {
            'passkeys': passkeys,
            'has_totp': has_totp,
            'backup_count': backup_count,
            'title': 'MFA Settings',
        })


# ─── RE-AUTH GATE ────────────────────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class ReauthView(View):
    """Re-authenticate before sensitive actions (reveal banking, reset pw, manage passkeys)."""

    def get(self, request):
        next_url = request.GET.get('next', reverse('admin_mfa:settings'))
        has_webauthn = WebAuthnCredential.objects.filter(user=request.user).exists()
        has_totp = MFADevice.objects.filter(user=request.user, is_verified=True).exists()
        return render(request, 'admin/mfa/reauth.html', {
            'next': next_url,
            'has_webauthn': has_webauthn,
            'has_totp': has_totp,
            'title': 'Confirm Identity',
        })

    def post(self, request):
        next_url = request.POST.get('next', reverse('admin_mfa:settings'))
        method = request.POST.get('method', 'totp')
        has_webauthn = WebAuthnCredential.objects.filter(user=request.user).exists()
        has_totp = MFADevice.objects.filter(user=request.user, is_verified=True).exists()

        if _is_locked_out(request, 'reauth'):
            return render(request, 'admin/mfa/reauth.html', {
                'next': next_url,
                'has_webauthn': has_webauthn,
                'has_totp': has_totp,
                'error': _lockout_error(),
                'locked': True,
                'title': 'Confirm Identity',
            })

        if method == 'totp':
            raw_code = request.POST.get('code', '')
            code, validation_error = _validate_code(raw_code)
            if validation_error:
                return render(request, 'admin/mfa/reauth.html', {
                    'next': next_url,
                    'has_webauthn': has_webauthn,
                    'has_totp': has_totp,
                    'error': validation_error,
                    'title': 'Confirm Identity',
                })
            if MFAService.verify(request.user, code):
                _clear_attempts(request, 'reauth')
                request.session['admin_reauth_verified'] = True
                _audit(request.user, 'REAUTH_TOTP', request)
                return redirect(next_url)

            locked, remaining = _record_failed_attempt(request, 'reauth')
            _audit(request.user, 'REAUTH_FAIL_TOTP', request, {'remaining': remaining})
            error = _lockout_error() if locked else f'Invalid code. {remaining} attempt(s) remaining.'
            return render(request, 'admin/mfa/reauth.html', {
                'next': next_url,
                'has_webauthn': has_webauthn,
                'has_totp': has_totp,
                'error': error,
                'locked': locked,
                'title': 'Confirm Identity',
            })

        elif method == 'email_otp':
            # Send or verify email OTP for reauth
            action = request.POST.get('email_action', 'verify')
            if action == 'send':
                otp = _generate_email_otp()
                request.session['_reauth_email_otp'] = otp
                request.session['_reauth_email_otp_expires'] = (
                    timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
                ).isoformat()
                try:
                    _send_otp_email(request.user, otp)
                    _audit(request.user, 'REAUTH_EMAIL_OTP_SENT', request)
                except Exception:
                    pass
                return render(request, 'admin/mfa/reauth.html', {
                    'next': next_url,
                    'has_webauthn': has_webauthn,
                    'has_totp': has_totp,
                    'email_otp_sent': True,
                    'title': 'Confirm Identity',
                })
            else:
                raw_code = request.POST.get('email_code', '')
                code, validation_error = _validate_code(raw_code)
                if validation_error:
                    return render(request, 'admin/mfa/reauth.html', {
                        'next': next_url,
                        'has_webauthn': has_webauthn,
                        'has_totp': has_totp,
                        'email_otp_sent': True,
                        'error': validation_error,
                        'title': 'Confirm Identity',
                    })

                stored = request.session.get('_reauth_email_otp')
                expires = request.session.get('_reauth_email_otp_expires')
                if not stored or not expires or timezone.now().isoformat() > expires:
                    return render(request, 'admin/mfa/reauth.html', {
                        'next': next_url,
                        'has_webauthn': has_webauthn,
                        'has_totp': has_totp,
                        'error': 'Code expired. Please request a new one.',
                        'title': 'Confirm Identity',
                    })

                if code == stored:
                    _clear_attempts(request, 'reauth')
                    request.session['admin_reauth_verified'] = True
                    request.session.pop('_reauth_email_otp', None)
                    request.session.pop('_reauth_email_otp_expires', None)
                    _audit(request.user, 'REAUTH_EMAIL_OTP', request)
                    return redirect(next_url)

                locked, remaining = _record_failed_attempt(request, 'reauth')
                _audit(request.user, 'REAUTH_FAIL_EMAIL_OTP', request, {'remaining': remaining})
                error = _lockout_error() if locked else f'Invalid code. {remaining} attempt(s) remaining.'
                return render(request, 'admin/mfa/reauth.html', {
                    'next': next_url,
                    'has_webauthn': has_webauthn,
                    'has_totp': has_totp,
                    'email_otp_sent': True,
                    'error': error,
                    'locked': locked,
                    'title': 'Confirm Identity',
                })

        return render(request, 'admin/mfa/reauth.html', {
            'next': next_url,
            'has_webauthn': has_webauthn,
            'has_totp': has_totp,
            'error': 'Unknown authentication method.',
            'title': 'Confirm Identity',
        })


# ─── PASSKEY MANAGEMENT (requires reauth) ────────────────────────────

def _require_reauth(request):
    """Check reauth flag. Returns redirect or None."""
    if not request.session.get('admin_reauth_verified'):
        next_url = request.get_full_path()
        return redirect(f"{reverse('admin_mfa:reauth')}?next={next_url}")
    return None


@method_decorator(staff_required, name='dispatch')
class DeletePasskeyView(View):
    def post(self, request, pk):
        gate = _require_reauth(request)
        if gate:
            return gate

        cred = WebAuthnCredential.objects.filter(pk=pk, user=request.user).first()
        if cred:
            device_name = cred.device_name
            cred.delete()
            _audit(request.user, 'WEBAUTHN_DELETE', request, {'device_name': device_name})
            request.session.pop('admin_reauth_verified', None)

        return redirect(reverse('admin_mfa:settings'))


@method_decorator(staff_required, name='dispatch')
class ResetMFAView(View):
    def post(self, request):
        gate = _require_reauth(request)
        if gate:
            return gate

        MFADevice.objects.filter(user=request.user).delete()
        MFABackupCode.objects.filter(user=request.user).delete()
        count = WebAuthnCredential.objects.filter(user=request.user).delete()[0]

        _audit(request.user, 'MFA_RESET', request, {'passkeys_deleted': count})
        request.session.pop('admin_mfa_verified', None)
        request.session.pop('admin_reauth_verified', None)

        return redirect(reverse('admin_mfa:setup'))


@method_decorator(staff_required, name='dispatch')
class RegenerateBackupCodesView(View):
    def post(self, request):
        gate = _require_reauth(request)
        if gate:
            return gate

        backup_codes = MFAService.generate_backup_codes(request.user)
        _audit(request.user, 'BACKUP_CODES_REGEN', request)
        request.session.pop('admin_reauth_verified', None)

        return render(request, 'admin/mfa/backup_codes.html', {
            'backup_codes': backup_codes,
            'title': 'New Backup Codes',
        })


# ─── Serialization helpers for fido2 objects ─────────────────────────

def _bytes_to_b64(value):
    import base64
    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.urlsafe_b64encode(bytes(value)).rstrip(b'=').decode('ascii')
    return value


def _serialize_registration(data):
    pk = data['publicKey'] if 'publicKey' in data else data
    result = {}
    result['rp'] = dict(pk['rp'])
    result['user'] = {
        'id': _bytes_to_b64(pk['user']['id']),
        'name': pk['user']['name'],
        'displayName': pk['user']['displayName'],
    }
    result['challenge'] = _bytes_to_b64(pk['challenge'])
    result['pubKeyCredParams'] = [dict(p) for p in pk['pubKeyCredParams']]
    if 'timeout' in pk:
        result['timeout'] = pk['timeout']
    if 'excludeCredentials' in pk:
        result['excludeCredentials'] = [{
            'type': c['type'],
            'id': _bytes_to_b64(c['id']),
        } for c in pk['excludeCredentials']]
    if 'authenticatorSelection' in pk:
        result['authenticatorSelection'] = dict(pk['authenticatorSelection'])
    if 'attestation' in pk:
        result['attestation'] = str(pk['attestation'])
    return result


def _serialize_authentication(data):
    pk = data['publicKey'] if 'publicKey' in data else data
    result = {}
    result['challenge'] = _bytes_to_b64(pk['challenge'])
    if 'timeout' in pk:
        result['timeout'] = pk['timeout']
    if 'rpId' in pk:
        result['rpId'] = pk['rpId']
    if 'allowCredentials' in pk:
        result['allowCredentials'] = [{
            'type': c['type'],
            'id': _bytes_to_b64(c['id']),
            **(({'transports': list(c['transports'])} if 'transports' in c else {})),
        } for c in pk['allowCredentials']]
    if 'userVerification' in pk:
        result['userVerification'] = str(pk['userVerification'])
    return result

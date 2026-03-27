from django.shortcuts import redirect
from django.urls import reverse

# Paths that don't require MFA (to avoid redirect loops)
MFA_EXEMPT_PATHS = [
    '/admin/login/',
    '/admin/logout/',
    '/admin/mfa/',
    '/admin/jsi18n/',
]


class AdminMFAMiddleware:
    """
    Enforce MFA for all staff/superuser access to /admin/.

    Flow:
    - MFA configured (TOTP/WebAuthn) -> redirect to /admin/mfa/verify/
    - MFA NOT configured -> redirect to /admin/mfa/email-otp/
      (email OTP sent automatically, user can setup full MFA later)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not path.startswith('/admin/'):
            return self.get_response(request)

        if any(path.startswith(exempt) for exempt in MFA_EXEMPT_PATHS):
            return self.get_response(request)

        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return self.get_response(request)

        if request.session.get('admin_mfa_verified'):
            return self.get_response(request)

        from app.models.auth_security import MFADevice, WebAuthnCredential
        has_totp = MFADevice.objects.filter(user=user, is_verified=True).exists()
        has_webauthn = WebAuthnCredential.objects.filter(user=user).exists()

        if has_totp or has_webauthn:
            return redirect(reverse('admin_mfa:verify'))
        else:
            # No MFA configured — fallback to email OTP
            return redirect(reverse('admin_mfa:email_otp'))

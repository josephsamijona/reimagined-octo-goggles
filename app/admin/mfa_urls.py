from django.urls import path
from . import mfa

app_name = 'admin_mfa'

urlpatterns = [
    # Email OTP (default for users without MFA)
    path('email-otp/', mfa.EmailOTPView.as_view(), name='email_otp'),

    # Setup prompt (shown after email OTP)
    path('setup-prompt/', mfa.SetupPromptView.as_view(), name='setup_prompt'),

    # Setup & verify
    path('setup/', mfa.MFASetupView.as_view(), name='setup'),
    path('verify/', mfa.MFAVerifyView.as_view(), name='verify'),

    # Settings dashboard
    path('settings/', mfa.MFASettingsView.as_view(), name='settings'),

    # Re-authentication gate
    path('reauth/', mfa.ReauthView.as_view(), name='reauth'),

    # WebAuthn JSON endpoints
    path('webauthn/register/begin/', mfa.WebAuthnRegisterBeginView.as_view(), name='webauthn_register_begin'),
    path('webauthn/register/complete/', mfa.WebAuthnRegisterCompleteView.as_view(), name='webauthn_register_complete'),
    path('webauthn/login/begin/', mfa.WebAuthnLoginBeginView.as_view(), name='webauthn_login_begin'),
    path('webauthn/login/complete/', mfa.WebAuthnLoginCompleteView.as_view(), name='webauthn_login_complete'),

    # Passkey management (requires reauth)
    path('passkey/<uuid:pk>/delete/', mfa.DeletePasskeyView.as_view(), name='delete_passkey'),
    path('reset/', mfa.ResetMFAView.as_view(), name='reset_mfa'),
    path('backup-codes/regenerate/', mfa.RegenerateBackupCodesView.as_view(), name='regen_backup_codes'),
]

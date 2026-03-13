import logging
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import login
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, JsonResponse
from django.db import transaction

from app.models import (
    OnboardingInvitation, OnboardingTrackingEvent,
    Language, InterpreterLanguage, ContractInvitation,
    User, Interpreter, InterpreterContractSignature
)

logger = logging.getLogger(__name__)


def encrypt_value(value):
    """Encrypt a value using the project's Fernet encryption."""
    if not value:
        return value
    try:
        encrypted = InterpreterContractSignature.encrypt_data(value)
        return encrypted.decode() if isinstance(encrypted, bytes) else encrypted
    except Exception:
        logger.warning("Encryption failed, storing value as-is")
        return value


def decrypt_value(value):
    """Decrypt a value using the project's Fernet encryption."""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            value = value.encode()
        return InterpreterContractSignature.decrypt_data(value) or ''
    except Exception:
        return value if isinstance(value, str) else ''


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_onboarding_invitation(request):
    """Helper to load onboarding invitation from session or user."""
    invitation_id = request.session.get('dbdint:onboarding_invitation_id')
    logger.info(f"get_onboarding_invitation: session invitation_id='{invitation_id}'")
    if invitation_id:
        try:
            inv = OnboardingInvitation.objects.get(id=invitation_id)
            logger.info(f"get_onboarding_invitation: Found invitation {inv.invitation_number} in session.")
            return inv
        except OnboardingInvitation.DoesNotExist:
            logger.warning(f"get_onboarding_invitation: Invitation ID '{invitation_id}' not found in DB.")
            
    # Fallback: Look up by authenticated user if available
    logger.info(f"get_onboarding_invitation: Falling back to authenticated user (is_auth={request.user.is_authenticated})")
    if request.user.is_authenticated:
        # Get the most recent invitation for this user
        invitation = OnboardingInvitation.objects.filter(user=request.user).order_by('-created_at').first()
        if invitation:
            logger.info(f"get_onboarding_invitation: Found invitation {invitation.invitation_number} via user {request.user.email}")
            # Restore session variable for subsequent calls
            request.session['dbdint:onboarding_invitation_id'] = str(invitation.id)
            return invitation
        else:
            logger.warning(f"get_onboarding_invitation: No invitation found for authenticated user {request.user.email}")
            
    logger.error("get_onboarding_invitation: No invitation found in session OR via authenticated user.")
    return None


# Phase routing map
PHASE_REDIRECT_MAP = {
    'INVITED': 'dbdint:onboarding_welcome',
    'EMAIL_OPENED': 'dbdint:onboarding_welcome',
    'WELCOME_VIEWED': 'dbdint:onboarding_account',
    'ACCOUNT_CREATED': 'dbdint:onboarding_profile',
    'PROFILE_COMPLETED': 'dbdint:onboarding_contract',
    'CONTRACT_STARTED': 'dbdint:onboarding_contract',
    'COMPLETED': 'dbdint:onboarding_complete',
}


@method_decorator(never_cache, name='dispatch')
class OnboardingEntryView(View):
    """
    Token-based entry point. Validates token, sets session, routes to correct phase.
    URL: /onboarding/<str:token>/
    """
    def get(self, request, token):
        logger.info(f"OnboardingEntryView.get: Received token='{token[:8]}...'")
        invitation = get_object_or_404(OnboardingInvitation, token=token)
        logger.info(f"OnboardingEntryView.get: Loaded invitation {invitation.invitation_number} (Phase: {invitation.current_phase})")

        # Check expired/voided (but allow completed ones to pass)
        if invitation.current_phase == 'VOIDED':
            logger.warning(f"OnboardingEntryView.get: Invitation {invitation.invitation_number} is VOIDED.")
            return render(request, 'contract/wrongclick.html', {'error': 'This invitation has been voided.'})
            
        if invitation.is_expired() and invitation.current_phase != 'COMPLETED':
            logger.warning(f"OnboardingEntryView.get: Invitation {invitation.invitation_number} is EXPIRED (expires_at={invitation.expires_at}).")
            if invitation.current_phase != 'EXPIRED':
                invitation.current_phase = 'EXPIRED'
                invitation.save(update_fields=['current_phase'])
            return render(request, 'contract/wrongclick.html', {'error': 'This invitation has expired.'})

        if invitation.current_phase == 'EXPIRED':
             logger.warning(f"OnboardingEntryView.get: Invitation {invitation.invitation_number} has EXPIRED phase.")
             return render(request, 'contract/wrongclick.html', {'error': 'This invitation has expired.'})

        # Store invitation in session
        request.session['dbdint:onboarding_invitation_id'] = str(invitation.id)
        logger.info(f"OnboardingEntryView.get: Stored invitation.id={invitation.id} in session.")

        # Track link click (first time only)
        if invitation.current_phase == 'INVITED':
            logger.info(f"OnboardingEntryView.get: Tracking LINK_CLICKED for {invitation.invitation_number}")
            OnboardingTrackingEvent.objects.create(
                invitation=invitation,
                event_type='LINK_CLICKED',
                metadata={'ip': get_client_ip(request), 'user_agent': request.META.get('HTTP_USER_AGENT', '')}
            )

        # If account already created or completed, auto-login the user
        if invitation.user and invitation.current_phase in ('ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED', 'COMPLETED'):
            logger.info(f"OnboardingEntryView.get: Attempting auto-login for user {invitation.user.email}")
            if not request.user.is_authenticated or request.user != invitation.user:
                login(request, invitation.user, backend='django.contrib.auth.backends.ModelBackend')
                logger.info("OnboardingEntryView.get: Auto-login successful.")
                # Re-store invitation ID after login (session rotation)
                request.session['dbdint:onboarding_invitation_id'] = str(invitation.id)

        # Route to correct phase
        redirect_name = PHASE_REDIRECT_MAP.get(invitation.current_phase, 'dbdint:onboarding_welcome')
        logger.info(f"OnboardingEntryView.get: Redirecting to {redirect_name} based on phase {invitation.current_phase}")
        return redirect(redirect_name)

@method_decorator(never_cache, name='dispatch')
class OnboardingWelcomeView(View):
    """
    Phase 1: Interactive welcome slides.
    URL: /onboarding/welcome/
    """
    template_name = 'onboarding/onboarding.html'

    def get(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation:
            logger.error("OnboardingWelcomeView.get: Invitation not found. Redirecting to contract_error.")
            return redirect('dbdint:contract_error')

        context = {
            'invitation': invitation,
            'phase': 'welcome',
            'first_name': invitation.first_name,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation:
            return redirect('dbdint:contract_error')

        # Mark welcome phase complete
        invitation.current_phase = 'WELCOME_VIEWED'
        invitation.welcome_viewed_at = timezone.now()
        invitation.save(update_fields=['current_phase', 'welcome_viewed_at'])

        OnboardingTrackingEvent.objects.create(
            invitation=invitation,
            event_type='WELCOME_COMPLETED',
            metadata={'ip': get_client_ip(request)}
        )

        return redirect('dbdint:onboarding_account')


@method_decorator(never_cache, name='dispatch')
class OnboardingAccountView(View):
    """
    Phase 2: Account creation (User + Interpreter).
    URL: /onboarding/create-account/
    """
    template_name = 'onboarding/onboarding.html'

    def get(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation:
            logger.error("OnboardingAccountView.get: Invitation not found. Redirecting to contract_error.")
            return redirect('dbdint:contract_error')

        # If account already created, skip to next phase
        if invitation.user:
            return redirect('dbdint:onboarding_profile')

        # Check if a user with this email already exists
        existing_user = User.objects.filter(email=invitation.email).first()

        context = {
            'invitation': invitation,
            'phase': 'account',
            'first_name': invitation.first_name,
            'last_name': invitation.last_name,
            'email': invitation.email,
            'phone': invitation.phone,
            'existing_user': existing_user is not None,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation:
            return redirect('dbdint:contract_error')

        # If account already exists, just skip
        if invitation.user:
            return redirect('dbdint:onboarding_profile')

        # Check if existing user with this email
        existing_user = User.objects.filter(email=invitation.email).first()

        if existing_user:
            # Existing user - verify password and link
            password = request.POST.get('password', '')
            if not existing_user.check_password(password):
                messages.error(request, 'Invalid password. Please try again.')
                return self.get(request)

            # Link existing user/interpreter to onboarding
            invitation.user = existing_user
            interpreter = getattr(existing_user, 'interpreter', None)
            
            # --- FIX: Ensure interpreter profile exists ---
            interpreter, created = Interpreter.objects.get_or_create(
                user=existing_user,
                defaults={'active': True}
            )
            if created:
                logger.info(f"OnboardingAccountView.post: Created new interpreter profile for existing user {existing_user.email}")
            else:
                logger.info(f"OnboardingAccountView.post: Found existing interpreter profile for user {existing_user.email}")
            
            invitation.interpreter = interpreter
            # -----------------------------------------------

            invitation.current_phase = 'ACCOUNT_CREATED'
            invitation.account_created_at = timezone.now()
            invitation.save()

            login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['dbdint:onboarding_invitation_id'] = str(invitation.id)

            OnboardingTrackingEvent.objects.create(
                invitation=invitation,
                event_type='ACCOUNT_CREATED',
                metadata={'ip': get_client_ip(request), 'existing_user': True}
            )

            return redirect('dbdint:onboarding_profile')

        # New user - validate form
        username = request.POST.get('username', '').strip()
        email = invitation.email  # Use email from invitation (readonly)
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip() or invitation.first_name
        last_name = request.POST.get('last_name', '').strip() or invitation.last_name
        phone = request.POST.get('phone', '').strip() or invitation.phone

        # Validation
        errors = []
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('This username is already taken.')
        if not password1 or len(password1) < 8:
            errors.append('Password must be at least 8 characters.')
        if password1 != password2:
            errors.append('Passwords do not match.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return self.get(request)

        try:
            with transaction.atomic():
                # Create User
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role='INTERPRETER'
                )

                # Create Interpreter profile
                interpreter = Interpreter.objects.create(
                    user=user,
                    active=True
                )

                # Link to invitation
                invitation.user = user
                invitation.interpreter = interpreter
                invitation.current_phase = 'ACCOUNT_CREATED'
                invitation.account_created_at = timezone.now()
                invitation.save()

            # Auto-login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['dbdint:onboarding_invitation_id'] = str(invitation.id)

            OnboardingTrackingEvent.objects.create(
                invitation=invitation,
                event_type='ACCOUNT_CREATED',
                metadata={'ip': get_client_ip(request), 'existing_user': False}
            )

            return redirect('dbdint:onboarding_profile')

        except Exception as e:
            logger.error(f"Error creating account during onboarding: {e}", exc_info=True)
            messages.error(request, 'An error occurred creating your account. Please try again.')
            return self.get(request)


@method_decorator(never_cache, name='dispatch')
class OnboardingProfileView(View):
    """
    Phase 3: Interpreter profile setup (languages, certifications, experience, banking).
    URL: /onboarding/profile/
    """
    template_name = 'onboarding/onboarding.html'

    def get(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation or not invitation.interpreter:
            logger.error(f"OnboardingProfileView.get: Invalid state (invITATION={'Yes' if invitation else 'No'}, interpreter={'Yes' if invitation and invitation.interpreter else 'No'}). Redirecting to contract_error.")
            return redirect('dbdint:contract_error')

        interpreter = invitation.interpreter
        existing_languages = InterpreterLanguage.objects.filter(interpreter=interpreter)
        existing_language_ids = list(existing_languages.values_list('language_id', flat=True))

        primary_lang = existing_languages.filter(is_primary=True).first()
        primary_language_id = primary_lang.language_id if primary_lang else None

        existing_cert = interpreter.certifications or {}

        context = {
            'invitation': invitation,
            'phase': 'profile',
            'interpreter': interpreter,
            'all_languages': Language.objects.filter(is_active=True).order_by('name'),
            'existing_language_ids': existing_language_ids,
            'primary_language_id': primary_language_id,
            'certified': existing_cert.get('certified', False),
            'cert_type': existing_cert.get('type', ''),
            'cert_number': existing_cert.get('number', ''),
            'date_of_birth': interpreter.date_of_birth.isoformat() if interpreter.date_of_birth else '',
            'years_exp': interpreter.years_of_experience or '',
            'assignment_types': interpreter.assignment_types or [],
            'preferred_type': interpreter.preferred_assignment_type or '',
            'radius': interpreter.radius_of_service or '',
            'cities': ', '.join(interpreter.cities_willing_to_cover or []) if isinstance(interpreter.cities_willing_to_cover, list) else (interpreter.cities_willing_to_cover or ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation or not invitation.interpreter:
            return redirect('dbdint:contract_error')

        interpreter = invitation.interpreter

        try:
            # Address
            interpreter.address = request.POST.get('address', '').strip()
            interpreter.city = request.POST.get('city', '').strip()
            interpreter.state = request.POST.get('state', '').strip()
            interpreter.zip_code = request.POST.get('zip_code', '').strip()

            # Date of birth
            dob = request.POST.get('date_of_birth', '').strip()
            if dob:
                interpreter.date_of_birth = dob

            # Profile photo
            if 'profile_image' in request.FILES:
                from custom_storages import MediaStorage
                photo = request.FILES['profile_image']
                allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if photo.content_type not in allowed_image_types:
                    messages.error(request, 'Profile photo must be a JPG, PNG, GIF or WEBP image.')
                    return self.get(request)
                if photo.size > 5 * 1024 * 1024:
                    messages.error(request, 'Profile photo must be less than 5MB.')
                    return self.get(request)
                storage = MediaStorage()
                filename = f"profiles/{interpreter.id}/{photo.name}"
                saved_path = storage.save(filename, photo)
                interpreter.profile_image = saved_path

            # Languages
            languages_ids = request.POST.getlist('languages')
            primary_language_id = request.POST.get('primary_language')

            # Certification
            certified = request.POST.get('certified') == 'yes'
            cert_type = request.POST.get('cert_type', '').strip() if certified else ''
            cert_number = request.POST.get('cert_number', '').strip() if certified else ''

            # Experience & Preferences
            years_exp = request.POST.get('years_of_experience', '')
            assignment_types = request.POST.getlist('assignment_types')
            preferred_type = request.POST.get('preferred_assignment_type', '')
            radius = request.POST.get('radius_of_service', '')
            cities = request.POST.get('cities_willing_to_cover', '')

            # Update interpreter
            interpreter.years_of_experience = years_exp
            interpreter.assignment_types = assignment_types
            interpreter.preferred_assignment_type = preferred_type
            try:
                interpreter.radius_of_service = int(radius) if radius else None
            except (ValueError, TypeError):
                interpreter.radius_of_service = None
                logger.warning(f"Invalid radius value provided: {radius}")
            interpreter.cities_willing_to_cover = [c.strip() for c in cities.split(',') if c.strip()]
            interpreter.certifications = {
                'certified': certified,
                'type': cert_type,
                'number': cert_number,
            }
            interpreter.save()

            # Handle certificate document uploads
            cert_files = request.FILES.getlist('cert_documents')
            if cert_files:
                from app.models import Document
                from custom_storages import MediaStorage
                storage = MediaStorage()
                allowed_cert_types = [
                    'application/pdf', 'image/jpeg', 'image/png', 'image/gif',
                ]
                for cert_file in cert_files:
                    if cert_file.content_type not in allowed_cert_types:
                        continue  # Skip unsupported file types
                    if cert_file.size > 10 * 1024 * 1024:
                        continue  # Skip files over 10MB
                    filename = f"certificates/{interpreter.id}/{cert_file.name}"
                    saved_path = storage.save(filename, cert_file)
                    
                    # --- FIX APPLIED HERE ---
                    Document.objects.create(
                        document_type='CERTIFICATE',
                        title=cert_file.name,
                        status='DRAFT',
                        user=invitation.user,  # Link directly to the User
                        file=saved_path,       # Store the file path
                        metadata={'interpreter_name': invitation.full_name} # Store name in metadata
                    )
                    # -------------------------

            # Update/Create InterpreterLanguage entries
            InterpreterLanguage.objects.filter(interpreter=interpreter).delete()
            for lang_id in languages_ids:
                try:
                    lang = Language.objects.get(id=lang_id)
                    is_primary = (str(lang_id) == str(primary_language_id))
                    InterpreterLanguage.objects.create(
                        interpreter=interpreter,
                        language=lang,
                        is_primary=is_primary,
                        certified=certified,
                        proficiency='PROFESSIONAL'
                    )
                except Language.DoesNotExist:
                    continue

            # Update phase
            invitation.current_phase = 'PROFILE_COMPLETED'
            invitation.profile_completed_at = timezone.now()
            invitation.save(update_fields=['current_phase', 'profile_completed_at'])

            OnboardingTrackingEvent.objects.create(
                invitation=invitation,
                event_type='PROFILE_SAVED',
                metadata={'ip': get_client_ip(request)}
            )

            return redirect('dbdint:onboarding_contract')

        except Exception as e:
            logger.error(f"Error saving profile during onboarding: {e}", exc_info=True)
            messages.error(request, 'An error occurred saving your profile. Please try again.')
            return self.get(request)


@method_decorator(never_cache, name='dispatch')
class OnboardingContractBridgeView(View):
    """
    Phase 4: Creates ContractInvitation and redirects to existing contract wizard.
    URL: /onboarding/contract/
    """
    def get(self, request):
        invitation = get_onboarding_invitation(request)
        if not invitation or not invitation.interpreter:
            logger.error(f"OnboardingContractBridgeView.get: Invalid state (invITATION={'Yes' if invitation else 'No'}, interpreter={'Yes' if invitation and invitation.interpreter else 'No'}). Redirecting to contract_error.")
            return redirect('dbdint:contract_error')

        # Create ContractInvitation if not exists
        if not invitation.contract_invitation:
            contract_inv = ContractInvitation.objects.create(
                interpreter=invitation.interpreter,
                created_by=invitation.created_by,
                expires_at=invitation.expires_at
            )
            invitation.contract_invitation = contract_inv
            invitation.save(update_fields=['contract_invitation'])

        # Update phase
        if invitation.current_phase != 'CONTRACT_STARTED':
            invitation.current_phase = 'CONTRACT_STARTED'
            invitation.contract_started_at = timezone.now()
            invitation.save(update_fields=['current_phase', 'contract_started_at'])

            OnboardingTrackingEvent.objects.create(
                invitation=invitation,
                event_type='CONTRACT_STARTED',
                metadata={'contract_invitation_id': str(invitation.contract_invitation.id)}
            )

        # Set session for contract wizard
        request.session['invitation_id'] = str(invitation.contract_invitation.id)

        return redirect('dbdint:contract_wizard')


@method_decorator(never_cache, name='dispatch')
class OnboardingCompleteView(View):
    """
    Final success page after full onboarding completion.
    URL: /onboarding/complete/
    """
    template_name = 'onboarding/complete.html'

    def get(self, request):
        invitation = get_onboarding_invitation(request)
        context = {
            'invitation': invitation,
            'first_name': invitation.first_name if invitation else '',
        }
        return render(request, self.template_name, context)


@method_decorator(never_cache, name='dispatch')
class OnboardingTrackingPixelView(View):
    """
    Email tracking pixel for onboarding invitation emails.
    URL: /onboarding/track/<str:token>/pixel.png
    """
    def get(self, request, token):
        try:
            invitation = get_object_or_404(OnboardingInvitation, token=token)

            if not invitation.email_opened_at:
                invitation.email_opened_at = timezone.now()
                if invitation.current_phase == 'INVITED':
                    invitation.current_phase = 'EMAIL_OPENED'
                invitation.save(update_fields=['email_opened_at', 'current_phase'])

                OnboardingTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='EMAIL_OPENED',
                    metadata={
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': get_client_ip(request)
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to track onboarding email open for token {token}: {e}")

        # Return 1x1 transparent PNG
        pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        return HttpResponse(pixel, content_type='image/png')
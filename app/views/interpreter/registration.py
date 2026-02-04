import random
import socket
import time
import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.generic import FormView
import logging

from ...forms import (
    InterpreterRegistrationForm1,
    InterpreterRegistrationForm2,
    InterpreterRegistrationForm3
)
from ...models import Language, InterpreterContractSignature

logger = logging.getLogger(__name__)

@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep1View(FormView):
    template_name = 'trad/auth/step1.html'
    form_class = InterpreterRegistrationForm1
    success_url = reverse_lazy('dbdint:interpreter_registration_step2')

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"Dispatch called for InterpreterRegistrationStep1View - User authenticated: {request.user.is_authenticated}")
        
        if request.user.is_authenticated:
            logger.info(f"Authenticated user {request.user.email} attempting to access registration. Redirecting to dashboard.")
            return redirect('dbdint:interpreter_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        logger.info("Form validation successful for InterpreterRegistrationStep1View")
        
        try:
            session_data = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'phone': form.cleaned_data['phone']
            }
            self.request.session['dbdint:interpreter_registration_step1'] = session_data
            logger.info(f"Session data saved successfully for username: {session_data['username']}, email: {session_data['email']}")
            
        except Exception as e:
            logger.error(f"Error saving session data: {str(e)}")
            messages.error(self.request, 'An error occurred while saving your information.')
            return self.form_invalid(form)
        
        logger.info(f"Redirecting to step 2 for username: {session_data['username']}")
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning("Form validation failed for InterpreterRegistrationStep1View")
        logger.debug(f"Form errors: {form.errors}")
        
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get(self, request, *args, **kwargs):
        logger.info("GET request received for InterpreterRegistrationStep1View")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.info("POST request received for InterpreterRegistrationStep1View")
        logger.debug(f"POST data: {request.POST}")
        return super().post(request, *args, **kwargs)

@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep2View(FormView):
    template_name = 'trad/auth/step2.html'
    form_class = InterpreterRegistrationForm2
    success_url = reverse_lazy('dbdint:interpreter_registration_step3')

    def get_context_data(self, **kwargs):
        logger.info("Getting context data for InterpreterRegistrationStep2View")
        context = super().get_context_data(**kwargs)
        
        try:
            context['languages'] = Language.objects.filter(is_active=True)
            logger.debug(f"Found {context['languages'].count()} active languages")
            
            step2_data = self.request.session.get('dbdint:interpreter_registration_step2')
            if step2_data and 'languages' in step2_data:
                context['selected_languages'] = step2_data['languages']
                logger.debug(f"Retrieved previously selected languages: {step2_data['languages']}")
        except Exception as e:
            logger.error(f"Error getting context data: {str(e)}")
            
        return context

    def dispatch(self, request, *args, **kwargs):
        logger.info("Dispatch called for InterpreterRegistrationStep2View")
        
        if not request.session.get('dbdint:interpreter_registration_step1'):
            logger.warning("Step 1 data not found in session. Redirecting to step 1.")
            messages.error(request, 'Please complete step 1 first.')
            return redirect('dbdint:interpreter_registration_step1')
            
        logger.debug("Step 1 data found in session. Proceeding with step 2.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        logger.info("Form validation successful for InterpreterRegistrationStep2View")
        
        try:
            selected_languages = [str(lang.id) for lang in form.cleaned_data['languages']]
            logger.debug(f"Selected languages: {selected_languages}")
            
            self.request.session['dbdint:interpreter_registration_step2'] = {
                'languages': selected_languages
            }
            logger.info("Session data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving session data: {str(e)}")
            messages.error(self.request, 'An error occurred while saving your information.')
            return self.form_invalid(form)
            
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning("Form validation failed for InterpreterRegistrationStep2View")
        logger.debug(f"Form errors: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_initial(self):
        logger.info("Getting initial data for InterpreterRegistrationStep2View")
        initial = super().get_initial()
        
        try:
            step2_data = self.request.session.get('dbdint:interpreter_registration_step2')
            if step2_data and 'languages' in step2_data:
                initial['languages'] = [int(lang_id) for lang_id in step2_data['languages']]
                logger.debug(f"Retrieved initial languages data: {initial['languages']}")
        except Exception as e:
            logger.error(f"Error getting initial data: {str(e)}")
            
        return initial

    def get(self, request, *args, **kwargs):
        logger.info("GET request received for InterpreterRegistrationStep2View")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.info("POST request received for InterpreterRegistrationStep2View")
        logger.debug(f"POST data: {request.POST}")
        return super().post(request, *args, **kwargs)



@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep3View(FormView):
    template_name = 'trad/auth/step3.html'
    form_class = InterpreterRegistrationForm3 
    success_url = reverse_lazy('dbdint:new_interpreter_dashboard')

    def get_context_data(self, **kwargs):
        logger.info("Getting context data for InterpreterRegistrationStep3View")
        context = super().get_context_data(**kwargs)
        context['current_step'] = 3
        context['states'] = {
             'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
             'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
             'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
             'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
             'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
             'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
             'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
             'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
             'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
             'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
             'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
             'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
             'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
         }
        logger.debug(f"Context data prepared with {len(context['states'])} states")
        return context

    def dispatch(self, request, *args, **kwargs):
        logger.info("Dispatch called for InterpreterRegistrationStep3View")
        step1_exists = 'dbdint:interpreter_registration_step1' in request.session
        step2_exists = 'dbdint:interpreter_registration_step2' in request.session
        
        if not all([step1_exists, step2_exists]):
            logger.warning("Previous steps data missing")
            messages.error(request, 'Please complete previous steps first.')
            return redirect('dbdint:interpreter_registration_step1')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        logger.info("Form validation successful")
        try:
            step1_data = self.request.session['dbdint:interpreter_registration_step1']
            step2_data = self.request.session['dbdint:interpreter_registration_step2']
            
            # Création de l'utilisateur
            user = User.objects.create_user(
                username=step1_data['username'],
                email=step1_data['email'],
                password=step1_data['password'],
                first_name=step1_data['first_name'],
                last_name=step1_data['last_name'],
                phone=step1_data['phone'],
                role='INTERPRETER'
            )
            logger.info(f"User created: {user.email}")

            # Création de l'interprète
            interpreter = form.save(commit=False)
            interpreter.user = user
            interpreter.save()
            
            for language_id in step2_data['languages']:
                interpreter.languages.add(language_id)
            
            # Création du contrat
            otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            contract = InterpreterContractSignature(
                user=user,
                interpreter=interpreter,
                interpreter_name=f"{user.first_name} {user.last_name}",
                interpreter_email=user.email,
                interpreter_phone=user.phone,
                interpreter_address=f"{interpreter.address}, {interpreter.city}, {interpreter.state} {interpreter.zip_code}",
                token=str(uuid.uuid4()),
                otp_code=otp_code,
            )
            contract.save()
            logger.info(f"Contract created for interpreter: {interpreter.id}, token: {contract.token}")
            
            # Envoi de l'email avec le contrat
            self.send_contract_email(user, interpreter, contract)
            
            del self.request.session['dbdint:interpreter_registration_step1']
            del self.request.session['dbdint:interpreter_registration_step2']

            login(self.request, user)
            messages.success(self.request, 'Your interpreter account has been created successfully! Please check your email to sign the agreement contract.')
            return super().form_valid(form)

        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            messages.error(self.request, 'An error occurred while creating your account.')
            return redirect('dbdint:interpreter_registration_step1')

    def send_contract_email(self, user, interpreter, contract):
         """Sends the contract email to the interpreter with anti-spam optimization."""
         try:
             # Création d'un identifiant unique pour ce message
             message_id = f"<contract-{contract.id}-{uuid.uuid4()}@{socket.gethostname()}>"
             
             # Construction de l'URL absolue pour le lien de vérification
             verification_url = self.request.build_absolute_uri(
                 reverse('dbdint:contract_verification', kwargs={'token': contract.token})
             )
             
             # Préparation des données pour le template
             context = {
                 'interpreter_name': f"{user.first_name} {user.last_name}",
                 'token': contract.token,
                 'otp_code': contract.otp_code,
                 'verification_url': verification_url,  # Passez l'URL complète au template
                 'email': user.email  # Pour le lien de désabonnement
             }
             
             # Rendu du template HTML
             html_message = render_to_string('notifmail/esign_notif.html', context)
             plain_message = strip_tags(html_message)
             
             # Ligne d'objet en anglais - éviter les formulations qui déclenchent les filtres anti-spam
             subject = f"Your JH Bridge Interpreter Agreement - Signature Required"
             
             # Format professionnel pour l'adresse expéditeur
             from_email = f"JH Bridge Contracts <contracts@jhbridgetranslation.com>"
             
             # Création de l'email avec du texte brut comme corps principal
             email = EmailMultiAlternatives(
                 subject=subject,
                 body=plain_message,
                 from_email=from_email,
                 to=[user.email],
                 reply_to=['support@jhbridgetranslation.com']
             )
             
             # Ajout de la version HTML comme alternative
             email.attach_alternative(html_message, "text/html")
             
             # En-têtes optimisés pour la délivrabilité
             email.extra_headers = {
                 # En-têtes d'avant
                 'Message-ID': message_id,
                 'X-Entity-Ref-ID': str(contract.token),
                 'X-Mailer': 'JHBridge-ContractMailer/1.0',
                 'X-Contact-ID': str(user.id),
                 'List-Unsubscribe': f'<mailto:unsubscribe@jhbridgetranslation.com?subject=Unsubscribe-{user.email}>',
                 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                 'Precedence': 'bulk',
                 'Auto-Submitted': 'auto-generated',
                 'Feedback-ID': f'contract-{contract.id}:{user.id}:jhbridge:{int(time.time())}'
             }
             
             # Envoi de l'email
             email.send(fail_silently=False)
             
             logger.info(f"Contract agreement email sent to: {user.email} with Message-ID: {message_id}")
             
         except Exception as e:
             logger.error(f"Error sending contract email: {str(e)}", exc_info=True)

    def form_invalid(self, form):
        logger.warning(f"Form validation failed: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

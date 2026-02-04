from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView
import logging

from ...forms import ClientRegistrationForm1, ClientRegistrationForm2

logger = logging.getLogger(__name__)

@method_decorator(never_cache, name='dispatch')
class ClientRegistrationView(FormView):
    template_name = 'client/auth/step1.html'
    form_class = ClientRegistrationForm1
    success_url = reverse_lazy('dbdint:client_register_step2')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.registration_complete:
            return redirect('dbdint:client_dashboard')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            logger.info("Processing valid registration form step 1")
            
            # Créer l'utilisateur avec le rôle CLIENT
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data['phone'],
                role=User.Roles.CLIENT,
                registration_complete=False
            )

            # Connecter l'utilisateur
            login(self.request, user)
            
            logger.info(
                f"Step 1 completed successfully",
                extra={
                    'user_id': user.id,
                    'username': user.username,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )

            messages.success(self.request, "Personal information saved successfully. Please complete your company details.")
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Error processing registration form step 1",
                exc_info=True,
                extra={
                    'form_data': {
                        k: v for k, v in form.cleaned_data.items() 
                        if k not in ['password1', 'password2']
                    },
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )
            messages.error(self.request, "An error occurred during registration. Please try again.")
            return self.form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class ClientRegistrationStep2View(FormView):
    template_name = 'client/auth/step2.html'
    form_class = ClientRegistrationForm2
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get(self, request, *args, **kwargs):
        # Si l'utilisateur n'est pas authentifié, rediriger vers l'étape 1
        if not request.user.is_authenticated:
            messages.error(request, "Please complete step 1 first.")
            return redirect('dbdint:client_register')
            
        # Si l'utilisateur a déjà complété son inscription
        if request.user.registration_complete:
            return redirect('dbdint:client_dashboard')
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_data'] = {
                'username': self.request.user.username,
                'email': self.request.user.email,
                'first_name': self.request.user.first_name,
                'last_name': self.request.user.last_name,
                'phone': self.request.user.phone
            }
        return context

    def form_valid(self, form):
        try:
            logger.info("Processing valid registration form step 2")
            
            if not self.request.user.is_authenticated:
                messages.error(self.request, "Session expired. Please start over.")
                return redirect('dbdint:client_register')

            # Créer le profil client avec l'utilisateur existant
            client_profile = form.save(commit=False)
            client_profile.user = self.request.user
            client_profile.save()

            # Marquer l'inscription comme complète
            self.request.user.registration_complete = True
            self.request.user.save()
            
            logger.info(
                "Registration completed successfully",
                extra={
                    'user_id': self.request.user.id,
                    'username': self.request.user.username,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )

            messages.success(self.request, "Registration completed successfully! Welcome to JHBRIDGE.")
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Error processing registration form step 2",
                exc_info=True,
                extra={
                    'form_data': form.cleaned_data,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )
            raise

    def form_invalid(self, form):
        logger.warning(
            "Invalid registration form step 2 submission",
            extra={
                'errors': form.errors,
                'ip_address': self.request.META.get('REMOTE_ADDR')
            }
        )
        return super().form_invalid(form)

class RegistrationSuccessView(TemplateView):
    template_name = 'client/auth/success.html'

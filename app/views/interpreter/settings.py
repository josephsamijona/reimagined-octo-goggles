from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ...forms import (
    InterpreterProfileForm,
    NotificationPreferenceForm,
    CustomPasswordtradChangeForm
)
from ...models import NotificationPreference

class InterpreterSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/settings.html'
    
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_notification_preferences(self):
        try:
            return NotificationPreference.objects.get(user=self.request.user)
        except NotificationPreference.DoesNotExist:
            return NotificationPreference.objects.create(
                user=self.request.user,
                email_quote_updates=True,
                email_assignment_updates=True,
                email_payment_updates=True,
                sms_enabled=False,
                quote_notifications=True,
                assignment_notifications=True,
                payment_notifications=True,
                system_notifications=True,
                notification_frequency='immediate',
                preferred_language=None
            )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # S'assure que les préférences de notification existent
        notification_preference = self.get_notification_preferences()
        
        if self.request.POST:
            context['profile_form'] = InterpreterProfileForm(
                self.request.POST, 
                self.request.FILES,
                user=user,
                instance=user.interpreter_profile
            )
            context['notification_form'] = NotificationPreferenceForm(
                self.request.POST,
                instance=notification_preference
            )
            context['password_form'] = CustomPasswordtradChangeForm(user, self.request.POST)
        else:
            context['profile_form'] = InterpreterProfileForm(
                user=user,
                instance=user.interpreter_profile
            )
            context['notification_form'] = NotificationPreferenceForm(
                instance=notification_preference
            )
            context['password_form'] = CustomPasswordtradChangeForm(user)
        
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        action = request.POST.get('action')
        
        if action == 'update_profile':
            profile_form = context['profile_form']
            if profile_form.is_valid():
                profile = profile_form.save(commit=False)
                user = request.user
                
                # Mise à jour des informations utilisateur
                user.first_name = profile_form.cleaned_data['first_name']
                user.last_name = profile_form.cleaned_data['last_name']
                user.email = profile_form.cleaned_data['email']
                user.phone_number = profile_form.cleaned_data['phone_number']
                user.save()
                
                # Mise à jour des informations bancaires
                profile.bank_name = profile_form.cleaned_data['bank_name']
                profile.account_holder_name = profile_form.cleaned_data['account_holder']
                profile.account_number = profile_form.cleaned_data['account_number']
                profile.routing_number = profile_form.cleaned_data['routing_number']
                
                profile.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('dbdint:interpreter_settings')
                
        elif action == 'update_notifications':
            notification_form = context['notification_form']
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Notification preferences updated successfully!')
                return redirect('dbdint:interpreter_settings')
                
        elif action == 'change_password':
            password_form = context['password_form']
            if password_form.is_valid():
                password_form.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('dbdint:interpreter_settings')
        
        return self.render_to_response(context)

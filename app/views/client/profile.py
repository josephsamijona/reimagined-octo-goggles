from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from ...forms import (
    NotificationPreferencesForm,
    UserProfileForm,
    ClientProfileForm,
    ClientProfileUpdateForm,
    CustomPasswordChangeForm
)
from ...models import NotificationPreference, Client

class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferencesForm
    template_name = 'client/setnotifications.html'
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get_object(self, queryset=None):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference

    def form_valid(self, form):
        messages.success(self.request, 'Your notification preferences have been updated!')
        return super().form_valid(form)

class ProfileView(LoginRequiredMixin, TemplateView):
    """Main profile view that combines user and client profile forms"""
    template_name = 'client/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_form'] = UserProfileForm(instance=self.request.user)
        context['client_form'] = ClientProfileForm(instance=self.request.user.client_profile)
        return context

    def post(self, request, *args, **kwargs):
        user_form = UserProfileForm(request.POST, instance=request.user)
        client_form = ClientProfileForm(request.POST, instance=request.user.client_profile)

        if user_form.is_valid() and client_form.is_valid():
            user_form.save()
            client_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('dbdint:client_profile_edit')
        
        return self.render_to_response(
            self.get_context_data(
                user_form=user_form,
                client_form=client_form
            )
        )
        
        
class ClientProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientProfileUpdateForm
    template_name = 'accounts/profile/update.html'
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get_object(self, queryset=None):
        return self.request.user.client_profile

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return super().form_valid(form)


class ProfilePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """View for changing password"""
    form_class = CustomPasswordChangeForm
    template_name = 'client/change_password.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)

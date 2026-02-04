import logging
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from ..forms import LoginForm

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = 'login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        logger.info(f"Determining success URL for user {user.id} with role {user.role}")
        
        try:
            if user.role == 'CLIENT':
                logger.debug(f"User {user.id} identified as CLIENT, redirecting to client dashboard")
                return reverse_lazy('dbdint:client_dashboard')
            
            logger.debug(f"User {user.id} identified as INTERPRETER, redirecting to interpreter dashboard")
            return reverse_lazy('dbdint:new_interpreter_dashboard')
            
        except Exception as e:
            logger.error(f"Error in get_success_url for user {user.id}: {str(e)}", exc_info=True)
            raise

    def form_invalid(self, form):
        logger.warning(
            "Login attempt failed",
            extra={
                'errors': form.errors,
                'cleaned_data': form.cleaned_data,
                'ip_address': self.request.META.get('REMOTE_ADDR')
            }
        )
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)

    def form_valid(self, form):
        logger.info(f"Successful login for user: {form.get_user().id}")
        return super().form_valid(form)

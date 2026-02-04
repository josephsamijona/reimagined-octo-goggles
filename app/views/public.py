from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, TemplateView

from ..forms import PublicQuoteRequestForm, ContactForm
from ..models import PublicQuoteRequest, ContactMessage

class ChooseRegistrationTypeView(TemplateView):
    template_name = 'choose_registration.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.role == 'CLIENT':
                return redirect('dbdint:client_dashboard')
            return redirect('dbdint:interpreter_dashboard')
        return super().dispatch(request, *args, **kwargs)



class PublicQuoteRequestView(CreateView):
    model = PublicQuoteRequest
    form_class = PublicQuoteRequestForm
    template_name = 'public/quote_request_form.html'
    success_url = reverse_lazy('dbdint:quote_request_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Request a Quote'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        quote_request = self.object

        # Send confirmation email to customer
        customer_context = {
            'quote_request': quote_request,
            'name': quote_request.full_name,
        }
        customer_email_html = render_to_string('emails/quote_request_confirmation.html', customer_context)
        customer_email_txt = render_to_string('emails/quote_request_confirmation.txt', customer_context)

        send_mail(
            subject='Quote Request Received - JHBRIDGE',
            message=customer_email_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[quote_request.email],
            html_message=customer_email_html,
            fail_silently=False,
        )

        # Send notification to staff
        staff_context = {
            'quote_request': quote_request,
            'admin_url': self.request.build_absolute_uri(
                reverse('dbdint:app_publicquoterequest_change', args=[quote_request.id])
            )
        }
        staff_email_html = render_to_string('emails/quote_request_notification.html', staff_context)
        staff_email_txt = render_to_string('emails/quote_request_notification.txt', staff_context)

        send_mail(
            subject=f'New Quote Request: {quote_request.company_name}',
            message=staff_email_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.QUOTE_NOTIFICATION_EMAIL],
            html_message=staff_email_html,
            fail_silently=False,
        )

        messages.success(
            self.request,
            'Your quote request has been submitted successfully! '
            'We will contact you shortly with more information.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error with your submission. Please check the form and try again.'
        )
        return super().form_invalid(form)

class QuoteRequestSuccessView(TemplateView):
    template_name = 'public/quote_request_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Quote Request Submitted'
        return context
    
    
class ContactView(CreateView):
    model = ContactMessage
    form_class = ContactForm
    template_name = 'public/contact.html'
    success_url = reverse_lazy('dbdint:contact_success')

    def form_valid(self, form):
        response = super().form_valid(form)
        contact = self.object

        # Send confirmation email to the sender
        send_mail(
            subject='Thank you for contacting JHBRIDGE',
            message=f"""Dear {contact.name},

Thank you for contacting JHBRIDGE. We have received your message and will get back to you shortly.

Your message details:
Subject: {contact.subject}
Reference Number: #{contact.id}

Best regards,
JHBRIDGE Team""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            fail_silently=False,
        )

        # Send notification to staff
        send_mail(
            subject=f'New Contact Form Submission: {contact.subject}',
            message=f"""New contact form submission received:

From: {contact.name} <{contact.email}>
Subject: {contact.subject}

Message:
{contact.message}

View in admin panel: {self.request.build_absolute_uri(reverse('dbdint:app_contactmessage_change', args=[contact.id]))}""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_NOTIFICATION_EMAIL],
            fail_silently=False,
        )

        messages.success(
            self.request,
            'Your message has been sent successfully! We will contact you shortly.'
        )
        return response

class ContactSuccessView(TemplateView):
    template_name = 'public/contact_success.html'

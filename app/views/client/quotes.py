from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from ...forms import QuoteFilterForm, QuoteRequestForm, AssignmentFeedbackForm
from ...models import (
    QuoteRequest,
    ServiceType,
    Quote,
    Assignment
)

class ClientRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a client"""
    def test_func(self):
        return self.request.user.role == 'CLIENT'

class QuoteRequestListView(LoginRequiredMixin, ClientRequiredMixin, ListView):
    """
    Display all quote requests for the client with filtering and pagination
    """
    model = QuoteRequest
    template_name = 'client/quote_list.html'
    context_object_name = 'quotes'
    paginate_by = 10

    def get_queryset(self):
        queryset = QuoteRequest.objects.filter(
            client=self.request.user.client_profile
        ).order_by('-created_at')

        # Apply filters from form
        filter_form = QuoteFilterForm(self.request.GET)
        if filter_form.is_valid():
            # Status filter
            status = filter_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)

            # Date range filter
            date_from = filter_form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(requested_date__gte=date_from)

            date_to = filter_form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(requested_date__lte=date_to)

            # Service type filter
            service_type = filter_form.cleaned_data.get('service_type')
            if service_type:
                queryset = queryset.filter(service_type=service_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter form
        context['filter_form'] = QuoteFilterForm(self.request.GET)
        
        # Add choices for dropdowns
        context['status_choices'] = QuoteRequest.Status.choices
        # Pour le service_type, on doit faire une requête car c'est un modèle
        context['service_types'] = ServiceType.objects.filter(active=True).values_list('id', 'name')
        
        # Add statistics
        base_queryset = self.get_queryset()
        context['stats'] = {
            'pending_count': base_queryset.filter(status=QuoteRequest.Status.PENDING).count(),
            'processing_count': base_queryset.filter(status=QuoteRequest.Status.PROCESSING).count(),
            'quoted_count': base_queryset.filter(status=QuoteRequest.Status.QUOTED).count(),
            'accepted_count': base_queryset.filter(status=QuoteRequest.Status.ACCEPTED).count()
        }

        # Add current filters to context for pagination
        context['current_filters'] = self.request.GET.dict()
        if 'page' in context['current_filters']:
            del context['current_filters']['page']
            
        return context

class QuoteRequestCreateView(LoginRequiredMixin, ClientRequiredMixin, CreateView):
    """
    Create a new quote request
    """
    model = QuoteRequest
    form_class = QuoteRequestForm
    template_name = 'client/quote_create.html'
    success_url = reverse_lazy('dbdint:client_quote_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.client = self.request.user.client_profile
        form.instance.status = QuoteRequest.Status.PENDING
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            'Your quote request has been successfully submitted. Our team will review it shortly.'
        )
        return response

class QuoteRequestDetailView(LoginRequiredMixin, ClientRequiredMixin, DetailView):
    """
    Display detailed information about a quote request and its timeline
    """
    model = QuoteRequest
    template_name = 'client/quote_detail.html'
    context_object_name = 'quote_request'

    def get_queryset(self):
        return QuoteRequest.objects.filter(
            client=self.request.user.client_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quote_request = self.get_object()
        
        # Get related quote if exists
        try:
            context['quote'] = quote_request.quote
        except Quote.DoesNotExist:
            context['quote'] = None

        # Get related assignment if exists
        if context['quote'] and context['quote'].status == 'ACCEPTED':
            try:
                context['assignment'] = context['quote'].assignment
            except Assignment.DoesNotExist:
                context['assignment'] = None

        # Create timeline events
        timeline_events = [
            {
                'date': quote_request.created_at,
                'status': 'CREATED',
                'description': 'Quote request submitted'
            }
        ]
        
        # Add quote events if exists
        if context['quote']:
            timeline_events.append({
                'date': context['quote'].created_at,
                'status': 'QUOTED',
                'description': 'Quote generated and sent'
            })

        # Add assignment events if exists
        if context.get('assignment'):
            timeline_events.append({
                'date': context['assignment'].created_at,
                'status': 'ASSIGNED',
                'description': 'Interpreter assigned'
            })
            if context['assignment'].status == 'COMPLETED':
                timeline_events.append({
                    'date': context['assignment'].completed_at,
                    'status': 'COMPLETED',
                    'description': 'Service completed'
                })

        context['timeline_events'] = sorted(
            timeline_events,
            key=lambda x: x['date'],
            reverse=True
        )

        return context

class QuoteAcceptView(LoginRequiredMixin, ClientRequiredMixin, View):
    """
    Handle quote acceptance
    """
    def post(self, request, *args, **kwargs):
        quote = get_object_or_404(
            Quote,
            quote_request__client=request.user.client_profile,
            pk=kwargs['pk'],
            status='SENT'
        )

        try:
            quote.status = Quote.Status.ACCEPTED
            quote.save()
            
            messages.success(
                request,
                'Quote accepted successfully. Our team will assign an interpreter shortly.'
            )
            return redirect('dbdint:client_quote_detail', pk=quote.quote_request.pk)

        except Exception as e:
            messages.error(request, 'An error occurred while accepting the quote.')
            return redirect('dbdint:quote_detail', pk=quote.quote_request.pk)

class QuoteRejectView(LoginRequiredMixin, ClientRequiredMixin, View):
    """
    Handle quote rejection
    """
    def post(self, request, *args, **kwargs):
        quote = get_object_or_404(
            Quote,
            quote_request__client=request.user.client_profile,
            pk=kwargs['pk'],
            status='SENT'
        )

        try:
            quote.status = Quote.Status.REJECTED
            quote.save()
            
            messages.success(request, 'Quote rejected successfully.')
            return redirect('dbdint:client_quote_detail', pk=quote.quote_request.pk)

        except Exception as e:
            messages.error(request, 'An error occurred while rejecting the quote.')
            return redirect('dbdint:quote_detail', pk=quote.quote_request.pk)

class AssignmentDetailClientView(LoginRequiredMixin, ClientRequiredMixin, DetailView):
    """
    Display assignment details for the client
    """
    model = Assignment
    template_name = 'client/assignment_detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        return Assignment.objects.filter(
            client=self.request.user.client_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = self.get_object()

        # Add feedback form if assignment is completed and no feedback exists
        if (assignment.status == 'COMPLETED' and 
            not hasattr(assignment, 'assignmentfeedback')):
            context['feedback_form'] = AssignmentFeedbackForm()

        return context

    def post(self, request, *args, **kwargs):
        """Handle feedback submission"""
        assignment = self.get_object()
        
        if assignment.status != 'COMPLETED':
            messages.error(request, 'Feedback can only be submitted for completed assignments.')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        if hasattr(assignment, 'assignmentfeedback'):
            messages.error(request, 'Feedback has already been submitted for this assignment.')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        form = AssignmentFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.assignment = assignment
            feedback.created_by = request.user
            feedback.save()
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        context = self.get_context_data(object=assignment)
        context['feedback_form'] = form
        return self.render_to_response(context)

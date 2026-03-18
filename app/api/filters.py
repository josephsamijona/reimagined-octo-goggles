import django_filters
from app.models import (
    Assignment, Interpreter, QuoteRequest, Invoice, EmailLog, Lead,
    OnboardingInvitation, AuditLog, Expense, InterpreterPayment,
    PublicQuoteRequest, Campaign,
)


class AssignmentFilter(django_filters.FilterSet):
    start_time_after = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='gte')
    start_time_before = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='lte')
    date_from = django_filters.DateFilter(field_name='start_time', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='start_time', lookup_expr='date__lte')

    class Meta:
        model = Assignment
        fields = {
            'status': ['exact', 'in'],
            'interpreter': ['exact'],
            'client': ['exact'],
            'service_type': ['exact'],
            'source_language': ['exact'],
            'target_language': ['exact'],
            'state': ['exact'],
            'city': ['exact', 'icontains'],
            'is_paid': ['exact'],
        }


class InterpreterFilter(django_filters.FilterSet):
    language = django_filters.NumberFilter(field_name='languages', lookup_expr='exact')
    has_w9 = django_filters.BooleanFilter(field_name='w9_on_file')
    is_blocked = django_filters.BooleanFilter(field_name='is_manually_blocked')

    class Meta:
        model = Interpreter
        fields = {
            'state': ['exact'],
            'city': ['exact', 'icontains'],
            'active': ['exact'],
            'background_check_status': ['exact'],
        }


class QuoteRequestFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = QuoteRequest
        fields = {
            'status': ['exact'],
            'client': ['exact'],
            'service_type': ['exact'],
        }


class InvoiceFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='issued_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='issued_date', lookup_expr='lte')

    class Meta:
        model = Invoice
        fields = {
            'status': ['exact'],
            'client': ['exact'],
        }


class OnboardingFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = OnboardingInvitation
        fields = {
            'current_phase': ['exact'],
        }


class EmailLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='received_at', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='received_at', lookup_expr='date__lte')

    class Meta:
        model = EmailLog
        fields = {
            'category': ['exact'],
            'priority': ['exact'],
            'is_processed': ['exact'],
            'is_read': ['exact'],
        }


class LeadFilter(django_filters.FilterSet):
    class Meta:
        model = Lead
        fields = {
            'source': ['exact'],
            'stage': ['exact'],
            'assigned_to': ['exact'],
        }


class ExpenseFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date_incurred', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='date_incurred', lookup_expr='date__lte')

    class Meta:
        model = Expense
        fields = {
            'expense_type': ['exact'],
            'status': ['exact'],
        }


class InterpreterPaymentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='scheduled_date', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='scheduled_date', lookup_expr='date__lte')

    class Meta:
        model = InterpreterPayment
        fields = {
            'status': ['exact'],
            'interpreter': ['exact'],
        }


class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='timestamp', lookup_expr='date__gte')
    date_to = django_filters.DateFilter(field_name='timestamp', lookup_expr='date__lte')

    class Meta:
        model = AuditLog
        fields = {
            'user': ['exact'],
            'action': ['exact', 'icontains'],
            'model_name': ['exact'],
        }


class CampaignFilter(django_filters.FilterSet):
    class Meta:
        model = Campaign
        fields = {
            'channel': ['exact'],
            'status': ['exact'],
        }


class PublicQuoteRequestFilter(django_filters.FilterSet):
    class Meta:
        model = PublicQuoteRequest
        fields = {
            'processed': ['exact'],
        }

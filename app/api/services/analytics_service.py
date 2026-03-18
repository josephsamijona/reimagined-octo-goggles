"""Analytics and reporting service for dashboard metrics."""
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth, ExtractMonth
from django.utils import timezone
from datetime import timedelta
from app.models import (
    Assignment, QuoteRequest, PublicQuoteRequest, Quote,
    ClientPayment, Expense, Invoice,
)


def get_revenue_by_month(months=12):
    """Get revenue and expenses aggregated by month for last N months."""
    start_date = timezone.now() - timedelta(days=months * 30)
    revenue = (
        ClientPayment.objects
        .filter(status='COMPLETED', payment_date__gte=start_date)
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    expenses = (
        Expense.objects
        .filter(status__in=['APPROVED', 'PAID'], date_incurred__gte=start_date)
        .annotate(month=TruncMonth('date_incurred'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    return {'revenue': list(revenue), 'expenses': list(expenses)}


def get_revenue_by_service():
    """Revenue aggregated by service type."""
    return list(
        ClientPayment.objects
        .filter(status='COMPLETED', assignment__isnull=False)
        .values(service_name=F('assignment__service_type__name'))
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )


def get_revenue_by_client(limit=10):
    """Top clients by revenue."""
    return list(
        ClientPayment.objects
        .filter(status='COMPLETED')
        .values(client_name=F('client__company_name'))
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')[:limit]
    )


def get_revenue_by_language():
    """Revenue by target language."""
    return list(
        ClientPayment.objects
        .filter(status='COMPLETED', assignment__isnull=False)
        .values(language=F('assignment__target_language__name'))
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )


def get_pnl_monthly(months=12):
    """P&L by month for last N months."""
    start_date = timezone.now() - timedelta(days=months * 30)
    revenue = (
        ClientPayment.objects
        .filter(status='COMPLETED', payment_date__gte=start_date)
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(revenue=Sum('amount'))
        .order_by('month')
    )
    expenses = (
        Expense.objects
        .filter(status__in=['APPROVED', 'PAID'], date_incurred__gte=start_date)
        .annotate(month=TruncMonth('date_incurred'))
        .values('month')
        .annotate(expenses=Sum('amount'))
        .order_by('month')
    )
    # Merge into a single list
    rev_dict = {r['month']: r['revenue'] for r in revenue}
    exp_dict = {e['month']: e['expenses'] for e in expenses}
    all_months = sorted(set(list(rev_dict.keys()) + list(exp_dict.keys())))
    return [
        {
            'month': m,
            'revenue': rev_dict.get(m, 0),
            'expenses': exp_dict.get(m, 0),
            'net': (rev_dict.get(m, 0) or 0) - (exp_dict.get(m, 0) or 0),
        }
        for m in all_months
    ]


def get_conversion_funnel():
    """Marketing conversion funnel."""
    total_public = PublicQuoteRequest.objects.count()
    processed_public = PublicQuoteRequest.objects.filter(processed=True).count()
    total_quotes = QuoteRequest.objects.count()
    accepted_quotes = Quote.objects.filter(status='ACCEPTED').count()
    completed_assignments = Assignment.objects.filter(status='COMPLETED').count()
    return {
        'public_requests': total_public,
        'processed_requests': processed_public,
        'quote_requests': total_quotes,
        'accepted_quotes': accepted_quotes,
        'completed_assignments': completed_assignments,
    }

"""Admin dashboard viewset providing KPIs, alerts, charts, and today's missions."""
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Q, F, Case, When, Value, IntegerField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.api.permissions import IsAdminUser
from app.models import (
    Assignment, Interpreter, QuoteRequest, Invoice,
    InterpreterPayment, Expense, OnboardingInvitation,
    EmailLog, ClientPayment,
)

logger = logging.getLogger(__name__)

# Cache TTLs (seconds)
_CACHE_KPI     = 60    # KPIs — 1 minute
_CACHE_ALERTS  = 120   # Alerts — 2 minutes
_CACHE_CHART   = 3600  # Revenue chart — 1 hour (monthly data never changes mid-hour)
_CACHE_TODAY   = 60    # Today's missions — 1 minute
_CACHE_PAYROLL = 120   # Payroll KPIs — 2 minutes
_CACHE_QUOTES  = 120   # Quote pipeline — 2 minutes


class DashboardViewSet(ViewSet):
    """Admin dashboard data endpoints."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """Real-time key performance indicators."""
        cached = cache.get('dashboard_kpis')
        if cached is not None:
            return Response(cached)

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        active_assignments = Assignment.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
        ).count()

        available_interpreters = Interpreter.objects.filter(
            active=True,
            is_manually_blocked=False,
        ).count()

        pending_requests = QuoteRequest.objects.filter(
            status='PENDING',
        ).count()

        # Month-to-date revenue from client payments
        mtd_revenue = ClientPayment.objects.filter(
            status='COMPLETED',
            payment_date__gte=month_start,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        # Month-to-date expenses
        mtd_expenses = Expense.objects.filter(
            status__in=['APPROVED', 'PAID'],
            date_incurred__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Acceptance rate (confirmed / (confirmed + cancelled) in last 30d)
        last_30 = now - timedelta(days=30)
        decision_qs = Assignment.objects.filter(created_at__gte=last_30)
        confirmed = decision_qs.filter(status='CONFIRMED').count()
        cancelled = decision_qs.filter(status='CANCELLED').count()
        acceptance_rate = (
            round(confirmed / (confirmed + cancelled) * 100, 1)
            if (confirmed + cancelled) > 0
            else 0
        )

        no_show = decision_qs.filter(status='NO_SHOW').count()
        total_completed_or_noshow = decision_qs.filter(
            status__in=['COMPLETED', 'NO_SHOW']
        ).count()
        no_show_rate = (
            round(no_show / total_completed_or_noshow * 100, 1)
            if total_completed_or_noshow > 0
            else 0
        )

        unresolved_emails = EmailLog.objects.filter(
            is_processed=False,
        ).count()

        active_onboardings = OnboardingInvitation.objects.exclude(
            current_phase__in=['COMPLETED', 'VOIDED', 'EXPIRED']
        ).count()

        net_margin = mtd_revenue - mtd_expenses

        data = {
            'active_assignments': active_assignments,
            'available_interpreters': available_interpreters,
            'pending_requests': pending_requests,
            'mtd_revenue': str(mtd_revenue),
            'mtd_expenses': str(mtd_expenses),
            'net_margin': str(net_margin),
            'acceptance_rate': acceptance_rate,
            'no_show_rate': no_show_rate,
            'unresolved_emails': unresolved_emails,
            'active_onboardings': active_onboardings,
        }
        cache.set('dashboard_kpis', data, timeout=_CACHE_KPI)
        return Response(data)

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """Actionable alerts for the admin dashboard."""
        cached = cache.get('dashboard_alerts')
        if cached is not None:
            return Response(cached)

        now = timezone.now()
        three_days_ago = now - timedelta(days=3)

        unassigned = Assignment.objects.filter(
            status='PENDING',
            interpreter__isnull=True,
        ).values('id', 'start_time', 'city', 'state').order_by('start_time')[:20]

        stalled_onboardings = OnboardingInvitation.objects.exclude(
            current_phase__in=['COMPLETED', 'VOIDED', 'EXPIRED']
        ).filter(
            created_at__lte=three_days_ago,
        ).values(
            'id', 'invitation_number', 'first_name', 'last_name',
            'current_phase', 'created_at',
        )[:20]

        overdue_invoices = Invoice.objects.filter(
            status='SENT',
            due_date__lt=now.date(),
        ).values(
            'id', 'invoice_number', 'client__company_name', 'total', 'due_date',
        ).order_by('due_date')[:20]

        pending_stubs = InterpreterPayment.objects.filter(
            status='PENDING',
        ).values(
            'id', 'reference_number', 'interpreter__user__first_name',
            'interpreter__user__last_name', 'amount', 'scheduled_date',
        ).order_by('scheduled_date')[:20]

        # Background checks older than 1 year
        one_year_ago = (now - timedelta(days=365)).date()
        expired_bg = Interpreter.objects.filter(
            active=True,
            background_check_date__lt=one_year_ago,
        ).values(
            'id', 'user__first_name', 'user__last_name', 'background_check_date',
        )[:20]

        missing_w9 = Interpreter.objects.filter(
            active=True,
            w9_on_file=False,
        ).values(
            'id', 'user__first_name', 'user__last_name',
        )[:20]

        thirty_days_ago = now - timedelta(days=30)
        recently_paid = Invoice.objects.filter(
            status='PAID',
            updated_at__gte=thirty_days_ago,
        ).values(
            'id', 'invoice_number', 'client__company_name', 'total', 'updated_at',
        ).order_by('-updated_at')[:20]

        data = {
            'unassigned_assignments': list(unassigned),
            'stalled_onboardings': list(stalled_onboardings),
            'overdue_invoices': list(overdue_invoices),
            'pending_payment_stubs': list(pending_stubs),
            'expired_background_checks': list(expired_bg),
            'missing_w9': list(missing_w9),
            'recently_paid_invoices': list(recently_paid),
        }
        cache.set('dashboard_alerts', data, timeout=_CACHE_ALERTS)
        return Response(data)

    # ------------------------------------------------------------------
    # Revenue chart (last 12 months)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='revenue-chart')
    def revenue_chart(self, request):
        """Monthly revenue and expenses for the last 12 months."""
        cached = cache.get('dashboard_revenue_chart')
        if cached is not None:
            return Response(cached)

        now = timezone.now()
        twelve_months_ago = (now - timedelta(days=365)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        revenue_by_month = (
            ClientPayment.objects
            .filter(status='COMPLETED', payment_date__gte=twelve_months_ago)
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('total_amount'))
            .order_by('month')
        )

        expenses_by_month = (
            Expense.objects
            .filter(status__in=['APPROVED', 'PAID'], date_incurred__gte=twelve_months_ago)
            .annotate(month=TruncMonth('date_incurred'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        # Merge into a single list keyed by month
        revenue_map = {r['month'].strftime('%Y-%m'): r['total'] for r in revenue_by_month}
        expense_map = {e['month'].strftime('%Y-%m'): e['total'] for e in expenses_by_month}

        months = sorted(set(list(revenue_map.keys()) + list(expense_map.keys())))
        data = [
            {
                'month': m,
                'revenue': str(revenue_map.get(m, Decimal('0'))),
                'expenses': str(expense_map.get(m, Decimal('0'))),
            }
            for m in months
        ]

        cache.set('dashboard_revenue_chart', data, timeout=_CACHE_CHART)
        return Response(data)

    # ------------------------------------------------------------------
    # Today's missions
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='today-missions')
    def today_missions(self, request):
        """Assignments scheduled for today."""
        cache_key = f'dashboard_today_missions_{timezone.now().date()}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        today = timezone.now().date()
        assignments = (
            Assignment.objects
            .filter(start_time__date=today)
            .select_related(
                'interpreter__user',
                'client',
                'service_type',
                'source_language',
                'target_language',
            )
            .order_by('start_time')
        )

        data = []
        for a in assignments:
            interpreter_name = ''
            if a.interpreter and a.interpreter.user:
                interpreter_name = f"{a.interpreter.user.first_name} {a.interpreter.user.last_name}"
            client_display = a.client.company_name if a.client else (a.client_name or '')

            data.append({
                'id': a.id,
                'status': a.status,
                'start_time': a.start_time,
                'end_time': a.end_time,
                'interpreter': interpreter_name,
                'client': client_display,
                'service_type': a.service_type.name if a.service_type else '',
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'city': a.city,
                'state': a.state,
            })

        cache.set(cache_key, data, timeout=_CACHE_TODAY)
        return Response(data)

    # ------------------------------------------------------------------
    # Payroll KPIs
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='payroll-kpis')
    def payroll_kpis(self, request):
        """Payroll summary KPIs for the admin dashboard."""
        cached = cache.get('dashboard_payroll_kpis')
        if cached is not None:
            return Response(cached)

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        pending_agg = InterpreterPayment.objects.filter(
            status='PENDING',
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
            interpreters=Count('interpreter', distinct=True),
        )

        paid_this_month = InterpreterPayment.objects.filter(
            status='COMPLETED',
            processed_date__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        avg_payment = InterpreterPayment.objects.filter(
            status__in=['PENDING', 'PROCESSING', 'COMPLETED'],
        ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0')

        processing_agg = InterpreterPayment.objects.filter(
            status='PROCESSING',
        ).aggregate(total=Sum('amount'), count=Count('id'))

        data = {
            'total_pending_payments': str(pending_agg['total'] or Decimal('0')),
            'pending_payments_count': pending_agg['count'] or 0,
            'interpreters_pending_payment': pending_agg['interpreters'] or 0,
            'total_paid_this_month': str(paid_this_month),
            'total_processing_payments': str(processing_agg['total'] or Decimal('0')),
            'processing_payments_count': processing_agg['count'] or 0,
            'average_payment_amount': str(round(avg_payment, 2)),
        }
        cache.set('dashboard_payroll_kpis', data, timeout=_CACHE_PAYROLL)
        return Response(data)

    # ------------------------------------------------------------------
    # Quote pipeline summary
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='quote-pipeline-summary')
    def quote_pipeline_summary(self, request):
        """Quote requests grouped by status for pipeline/funnel view."""
        cached = cache.get('dashboard_quote_pipeline')
        if cached is not None:
            return Response(cached)

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        by_status = (
            QuoteRequest.objects
            .values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )
        status_map = {row['status']: row['count'] for row in by_status}

        recent_total = QuoteRequest.objects.filter(created_at__gte=thirty_days_ago).count()
        recent_accepted = QuoteRequest.objects.filter(
            status='ACCEPTED', updated_at__gte=thirty_days_ago
        ).count()
        recent_rejected = QuoteRequest.objects.filter(
            status='REJECTED', updated_at__gte=thirty_days_ago
        ).count()

        conversion_rate = (
            round(recent_accepted / recent_total * 100, 1)
            if recent_total > 0
            else 0
        )

        data = {
            'by_status': {
                'PENDING': status_map.get('PENDING', 0),
                'PROCESSING': status_map.get('PROCESSING', 0),
                'QUOTED': status_map.get('QUOTED', 0),
                'ACCEPTED': status_map.get('ACCEPTED', 0),
                'REJECTED': status_map.get('REJECTED', 0),
                'EXPIRED': status_map.get('EXPIRED', 0),
            },
            'last_30_days': {
                'total': recent_total,
                'accepted': recent_accepted,
                'rejected': recent_rejected,
                'conversion_rate': conversion_rate,
            },
        }
        cache.set('dashboard_quote_pipeline', data, timeout=_CACHE_QUOTES)
        return Response(data)

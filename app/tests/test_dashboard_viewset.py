"""Tests for app/api/viewsets/dashboard.py — DashboardViewSet."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _mock_aggregate(total=Decimal('0'), count=0, interpreters=0, avg=Decimal('0')):
    """Return a dict that mimics aggregate() output."""
    return {'total': total, 'count': count, 'interpreters': interpreters, 'avg': avg}


class DashboardKpisStructureTest(SimpleTestCase):
    """Test kpis endpoint returns expected keys."""

    @patch('app.api.viewsets.dashboard.OnboardingInvitation')
    @patch('app.api.viewsets.dashboard.EmailLog')
    @patch('app.api.viewsets.dashboard.Expense')
    @patch('app.api.viewsets.dashboard.ClientPayment')
    @patch('app.api.viewsets.dashboard.QuoteRequest')
    @patch('app.api.viewsets.dashboard.Interpreter')
    @patch('app.api.viewsets.dashboard.Assignment')
    def test_kpis_response_keys(
        self, MockAssignment, MockInterpreter, MockQuoteRequest,
        MockClientPayment, MockExpense, MockEmailLog, MockOnboarding
    ):
        from app.api.viewsets.dashboard import DashboardViewSet

        MockAssignment.objects.filter.return_value.count.return_value = 5
        MockInterpreter.objects.filter.return_value.count.return_value = 10
        MockQuoteRequest.objects.filter.return_value.count.return_value = 3

        MockClientPayment.objects.filter.return_value.aggregate.return_value = {'total': Decimal('5000')}
        MockExpense.objects.filter.return_value.aggregate.return_value = {'total': Decimal('2000')}

        # Decision queryset for acceptance rate
        decision_qs = MagicMock()
        decision_qs.filter.return_value.count.return_value = 0
        MockAssignment.objects.filter.return_value = decision_qs

        MockEmailLog.objects.filter.return_value.count.return_value = 2
        MockOnboarding.objects.exclude.return_value.count.return_value = 1

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.kpis(request)

        expected_keys = {
            'active_assignments', 'available_interpreters', 'pending_requests',
            'mtd_revenue', 'mtd_expenses', 'net_margin',
            'acceptance_rate', 'no_show_rate',
            'unresolved_emails', 'active_onboardings',
        }
        self.assertEqual(set(response.data.keys()), expected_keys)


class DashboardAlertsStructureTest(SimpleTestCase):
    """Test alerts endpoint returns expected keys."""

    @patch('app.api.viewsets.dashboard.Invoice')
    @patch('app.api.viewsets.dashboard.Interpreter')
    @patch('app.api.viewsets.dashboard.InterpreterPayment')
    @patch('app.api.viewsets.dashboard.OnboardingInvitation')
    @patch('app.api.viewsets.dashboard.Assignment')
    def test_alerts_response_keys(
        self, MockAssignment, MockOnboarding, MockPayment,
        MockInterpreter, MockInvoice
    ):
        from app.api.viewsets.dashboard import DashboardViewSet

        # Setup chain mocks for querysets
        MockAssignment.objects.filter.return_value.values.return_value \
            .order_by.return_value.__getitem__ = MagicMock(return_value=[])

        MockOnboarding.objects.exclude.return_value.filter.return_value \
            .values.return_value.__getitem__ = MagicMock(return_value=[])

        MockInvoice.objects.filter.return_value.values.return_value \
            .order_by.return_value.__getitem__ = MagicMock(return_value=[])

        MockPayment.objects.filter.return_value.values.return_value \
            .order_by.return_value.__getitem__ = MagicMock(return_value=[])

        MockInterpreter.objects.filter.return_value.values.return_value \
            .__getitem__ = MagicMock(return_value=[])

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.alerts(request)

        expected_keys = {
            'unassigned_assignments', 'stalled_onboardings',
            'overdue_invoices', 'pending_payment_stubs',
            'expired_background_checks', 'missing_w9',
            'recently_paid_invoices',
        }
        self.assertEqual(set(response.data.keys()), expected_keys)


class DashboardTodayMissionsTest(SimpleTestCase):
    """Test today_missions endpoint."""

    @patch('app.api.viewsets.dashboard.Assignment')
    def test_returns_list(self, MockAssignment):
        from app.api.viewsets.dashboard import DashboardViewSet

        MockAssignment.objects.filter.return_value.select_related.return_value \
            .order_by.return_value = []

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.today_missions(request)

        self.assertEqual(response.data, [])


class DashboardPayrollKpisStructureTest(SimpleTestCase):
    """Test payroll_kpis endpoint returns expected keys."""

    @patch('app.api.viewsets.dashboard.InterpreterPayment')
    def test_payroll_kpis_response_keys(self, MockPayment):
        from app.api.viewsets.dashboard import DashboardViewSet

        MockPayment.objects.filter.return_value.aggregate.return_value = {
            'total': Decimal('1000'), 'count': 5, 'interpreters': 3, 'avg': Decimal('200'),
        }

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.payroll_kpis(request)

        expected_keys = {
            'total_pending_payments', 'pending_payments_count',
            'interpreters_pending_payment', 'total_paid_this_month',
            'total_processing_payments', 'processing_payments_count',
            'average_payment_amount',
        }
        self.assertEqual(set(response.data.keys()), expected_keys)


class DashboardQuotePipelineStructureTest(SimpleTestCase):
    """Test quote_pipeline_summary endpoint returns expected structure."""

    @patch('app.api.viewsets.dashboard.QuoteRequest')
    def test_pipeline_response_keys(self, MockQuoteRequest):
        from app.api.viewsets.dashboard import DashboardViewSet

        MockQuoteRequest.objects.values.return_value.annotate.return_value \
            .order_by.return_value = []
        MockQuoteRequest.objects.filter.return_value.count.return_value = 0

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.quote_pipeline_summary(request)

        self.assertIn('by_status', response.data)
        self.assertIn('last_30_days', response.data)

        status_keys = {'PENDING', 'PROCESSING', 'QUOTED', 'ACCEPTED', 'REJECTED', 'EXPIRED'}
        self.assertEqual(set(response.data['by_status'].keys()), status_keys)

        last_30_keys = {'total', 'accepted', 'rejected', 'conversion_rate'}
        self.assertEqual(set(response.data['last_30_days'].keys()), last_30_keys)


class DashboardRevenueChartTest(SimpleTestCase):
    """Test revenue_chart endpoint returns list."""

    @patch('app.api.viewsets.dashboard.Expense')
    @patch('app.api.viewsets.dashboard.ClientPayment')
    def test_returns_list(self, MockClientPayment, MockExpense):
        from app.api.viewsets.dashboard import DashboardViewSet

        MockClientPayment.objects.filter.return_value.annotate.return_value \
            .values.return_value.annotate.return_value.order_by.return_value = []
        MockExpense.objects.filter.return_value.annotate.return_value \
            .values.return_value.annotate.return_value.order_by.return_value = []

        viewset = DashboardViewSet()
        request = MagicMock()
        response = viewset.revenue_chart(request)

        self.assertIsInstance(response.data, list)

"""Tests for app/api/viewsets/finance.py — FinanceViewSet logic."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


def _mock_invoice(**overrides):
    """Build a mock Invoice."""
    inv = MagicMock()
    inv.id = overrides.get('id', 1)
    inv.invoice_number = overrides.get('invoice_number', 'INV-2026-00001')
    inv.status = overrides.get('status', 'DRAFT')
    inv.total = overrides.get('total', '1000.00')
    inv.due_date = overrides.get('due_date', '2026-12-31')
    inv.issued_date = overrides.get('issued_date', None)
    inv.paid_date = overrides.get('paid_date', None)
    inv.reminder_count = overrides.get('reminder_count', 0)
    inv.last_reminder_sent = overrides.get('last_reminder_sent', None)
    inv.client = MagicMock()
    inv.client.user = MagicMock()
    inv.client.user.email = 'client@example.com'
    return inv


class RemindInvoiceNotificationTypeTest(SimpleTestCase):
    """Verify remind_invoice creates PAYMENT_REMINDER, not PAYMENT_RECEIVED."""

    @patch('app.models.Notification')
    def test_creates_payment_reminder_notification(self, MockNotification):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='SENT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.objects.select_related.return_value.get.return_value = invoice

            viewset.remind_invoice(request, invoice_id=1)

            MockNotification.objects.create.assert_called_once()
            call_kwargs = MockNotification.objects.create.call_args[1]
            self.assertEqual(call_kwargs['type'], 'PAYMENT_REMINDER')

    @patch('app.models.Notification')
    def test_notification_type_is_not_payment_received(self, MockNotification):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='OVERDUE')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.objects.select_related.return_value.get.return_value = invoice

            viewset.remind_invoice(request, invoice_id=1)

            call_kwargs = MockNotification.objects.create.call_args[1]
            self.assertNotEqual(call_kwargs['type'], 'PAYMENT_RECEIVED')


class InvoiceLifecycleGuardsTest(SimpleTestCase):
    """Test invoice status transition guards."""

    def test_send_rejects_non_draft(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='SENT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.objects.get.return_value = invoice
            response = viewset.send_invoice(request, invoice_id=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('Cannot send', response.data['detail'])

    def test_send_allows_draft(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='DRAFT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.Status.SENT = 'SENT'
            MockInvoice.objects.get.return_value = invoice
            response = viewset.send_invoice(request, invoice_id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice.status, 'SENT')

    def test_mark_paid_rejects_draft(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='DRAFT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.objects.get.return_value = invoice
            response = viewset.mark_paid(request, invoice_id=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('Cannot mark as paid', response.data['detail'])

    def test_mark_paid_allows_sent(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        request.data = {'payment_method': 'ACH'}
        invoice = _mock_invoice(status='SENT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.Status.PAID = 'PAID'
            MockInvoice.objects.get.return_value = invoice
            response = viewset.mark_paid(request, invoice_id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice.status, 'PAID')

    def test_mark_paid_allows_overdue(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        request.data = {}
        invoice = _mock_invoice(status='OVERDUE')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.Status.PAID = 'PAID'
            MockInvoice.objects.get.return_value = invoice
            response = viewset.mark_paid(request, invoice_id=1)

        self.assertEqual(response.status_code, 200)

    def test_remind_rejects_draft(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        invoice = _mock_invoice(status='DRAFT')

        with patch('app.api.viewsets.finance.Invoice') as MockInvoice:
            MockInvoice.objects.select_related.return_value.get.return_value = invoice
            response = viewset.remind_invoice(request, invoice_id=1)

        self.assertEqual(response.status_code, 400)


class ExpenseLifecycleGuardsTest(SimpleTestCase):
    """Test expense status transition guards."""

    def test_approve_rejects_non_pending(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        expense = MagicMock()
        expense.status = 'APPROVED'

        with patch('app.api.viewsets.finance.Expense') as MockExpense:
            MockExpense.objects.get.return_value = expense
            response = viewset.approve_expense(request, expense_id=1)

        self.assertEqual(response.status_code, 400)

    def test_approve_allows_pending(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        expense = MagicMock()
        expense.id = 1
        expense.status = 'PENDING'

        with patch('app.api.viewsets.finance.Expense') as MockExpense:
            MockExpense.objects.get.return_value = expense
            response = viewset.approve_expense(request, expense_id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expense.status, 'APPROVED')

    def test_pay_rejects_pending(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        expense = MagicMock()
        expense.status = 'PENDING'

        with patch('app.api.viewsets.finance.Expense') as MockExpense:
            MockExpense.objects.get.return_value = expense
            response = viewset.pay_expense(request, expense_id=1)

        self.assertEqual(response.status_code, 400)

    def test_pay_allows_approved(self):
        from app.api.viewsets.finance import FinanceViewSet

        viewset = FinanceViewSet()
        request = MagicMock()
        expense = MagicMock()
        expense.id = 1
        expense.status = 'APPROVED'

        with patch('app.api.viewsets.finance.Expense') as MockExpense:
            MockExpense.objects.get.return_value = expense
            response = viewset.pay_expense(request, expense_id=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expense.status, 'PAID')

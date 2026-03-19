"""Tests for app/api/viewsets/payroll.py — PayrollViewSet logic."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class BatchStubsUniqueDocNumberTest(SimpleTestCase):
    """Verify batch stub creation uses collision-safe document numbers."""

    @patch('app.api.viewsets.payroll.generate_unique_reference')
    @patch('app.api.viewsets.payroll.Service')
    @patch('app.models.Assignment')
    @patch('app.api.viewsets.payroll.PayrollDocument')
    @patch('app.api.viewsets.payroll.Interpreter')
    def test_calls_generate_unique_reference(
        self, MockInterpreter, MockPayrollDoc, MockAssignment, MockService, mock_gen_ref
    ):
        from app.api.viewsets.payroll import PayrollViewSet

        mock_gen_ref.return_value = 'PS-2026-12345'

        # Setup interpreter
        interp = MagicMock()
        interp.user.first_name = 'Jane'
        interp.user.last_name = 'Smith'
        interp.user.email = 'jane@example.com'
        interp.user.phone = '555-1234'
        interp.address = '123 Main St'
        interp.city = 'Boston'
        interp.state = 'MA'
        interp.zip_code = '02101'
        MockInterpreter.objects.filter.return_value.select_related.return_value = [interp]

        # Setup stub creation
        stub = MagicMock()
        stub.id = 1
        stub.document_number = 'PS-2026-12345'
        stub.interpreter_name = 'Jane Smith'
        MockPayrollDoc.objects.create.return_value = stub

        # No assignments to process
        MockAssignment.objects.filter.return_value.filter.return_value.filter.return_value \
            .select_related.return_value = []

        request = MagicMock()
        request.data = {
            'interpreter_ids': [1],
            'period_start': '2026-01-01',
            'period_end': '2026-01-31',
        }

        viewset = PayrollViewSet()
        response = viewset.batch_stubs(request)

        mock_gen_ref.assert_called_once_with('PS', MockPayrollDoc, 'document_number')
        self.assertEqual(response.status_code, 201)

    def test_batch_rejects_empty_interpreter_ids(self):
        from app.api.viewsets.payroll import PayrollViewSet

        request = MagicMock()
        request.data = {'interpreter_ids': []}

        viewset = PayrollViewSet()
        response = viewset.batch_stubs(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn('interpreter_ids', response.data['detail'])


class StubPdfEndpointTest(SimpleTestCase):
    """Test stub PDF generation endpoint."""

    @patch('app.api.viewsets.payroll.generate_payroll_pdf')
    @patch('app.api.viewsets.payroll.PayrollDocument')
    def test_returns_pdf_content_type(self, MockPayrollDoc, mock_gen_pdf):
        from app.api.viewsets.payroll import PayrollViewSet
        import io

        stub = MagicMock()
        stub.document_number = 'PS-2026-00001'
        MockPayrollDoc.objects.prefetch_related.return_value.get.return_value = stub
        MockPayrollDoc.DoesNotExist = Exception

        buffer = io.BytesIO(b'%PDF-1.4 fake')
        mock_gen_pdf.return_value = buffer

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.stub_pdf(request, stub_id=1)

        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('paystub-PS-2026-00001', response['Content-Disposition'])

    @patch('app.api.viewsets.payroll.PayrollDocument')
    def test_stub_pdf_returns_404_for_missing(self, MockPayrollDoc):
        from app.api.viewsets.payroll import PayrollViewSet

        # Set up DoesNotExist as a real exception type
        MockPayrollDoc.DoesNotExist = type('DoesNotExist', (Exception,), {})
        MockPayrollDoc.objects.prefetch_related.return_value.get.side_effect = \
            MockPayrollDoc.DoesNotExist()

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.stub_pdf(request, stub_id=999)

        self.assertEqual(response.status_code, 404)


class SendStubValidationTest(SimpleTestCase):
    """Test send_stub validates email presence."""

    @patch('app.api.viewsets.payroll.PayrollDocument')
    def test_rejects_stub_without_email(self, MockPayrollDoc):
        from app.api.viewsets.payroll import PayrollViewSet

        stub = MagicMock()
        stub.interpreter_email = ''
        MockPayrollDoc.objects.prefetch_related.return_value.get.return_value = stub
        MockPayrollDoc.DoesNotExist = type('DoesNotExist', (Exception,), {})

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.send_stub(request, stub_id=1)

        self.assertEqual(response.status_code, 400)
        self.assertIn('No interpreter email', response.data['detail'])


class ProcessPaymentGuardsTest(SimpleTestCase):
    """Test process_payment status guards."""

    @patch('app.api.viewsets.payroll.InterpreterPayment')
    def test_rejects_unprocessable_payment(self, MockPayment):
        from app.api.viewsets.payroll import PayrollViewSet

        payment = MagicMock()
        payment.status = 'COMPLETED'
        payment.can_be_processed.return_value = False
        MockPayment.objects.get.return_value = payment
        MockPayment.DoesNotExist = type('DoesNotExist', (Exception,), {})

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.process_payment(request, payment_id=1)

        self.assertEqual(response.status_code, 400)

    @patch('app.api.viewsets.payroll.InterpreterPayment')
    def test_processes_valid_payment(self, MockPayment):
        from app.api.viewsets.payroll import PayrollViewSet

        payment = MagicMock()
        payment.id = 1
        payment.reference_number = 'INT-1-ABC123'
        payment.status = 'PROCESSING'
        payment.can_be_processed.return_value = True
        MockPayment.objects.get.return_value = payment
        MockPayment.DoesNotExist = type('DoesNotExist', (Exception,), {})

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.process_payment(request, payment_id=1)

        self.assertEqual(response.status_code, 200)
        payment.mark_as_processing.assert_called_once()

    @patch('app.api.viewsets.payroll.InterpreterPayment')
    def test_returns_404_for_missing_payment(self, MockPayment):
        from app.api.viewsets.payroll import PayrollViewSet

        MockPayment.DoesNotExist = type('DoesNotExist', (Exception,), {})
        MockPayment.objects.get.side_effect = MockPayment.DoesNotExist()

        request = MagicMock()
        viewset = PayrollViewSet()
        response = viewset.process_payment(request, payment_id=999)

        self.assertEqual(response.status_code, 404)

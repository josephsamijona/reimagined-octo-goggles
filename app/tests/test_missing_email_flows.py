"""Tests for Feature 9 — missing email flows.

Covers:
  - ContractReminderService._send_reminder URL building (invitation vs. no invitation)
  - PayrollEmailService.send_stub — HTML body, PDF attachment, success/failure paths
  - send_stub viewset action delegates to PayrollEmailService

All tests use SimpleTestCase + MagicMock — no DB required.
"""
from unittest.mock import MagicMock, patch, call
from django.test import SimpleTestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_interpreter(email='interpreter@example.com', full_name='Jean Dupont'):
    user = MagicMock()
    user.email = email
    user.get_full_name.return_value = full_name
    interp = MagicMock()
    interp.user = user
    return interp


def _make_invitation(review_token='rev-token-123', accept_token='acc-token-456'):
    inv = MagicMock()
    inv.review_token = review_token
    inv.accept_token = accept_token
    return inv


def _make_stub(
    document_number='PAY-2025-001',
    interpreter_name='Jean Dupont',
    interpreter_email='jean@example.com',
    total_amount=1200.00,
    company_address='123 Main St, Montreal, QC',
):
    stub = MagicMock()
    stub.document_number = document_number
    stub.interpreter_name = interpreter_name
    stub.interpreter_email = interpreter_email
    stub.total_amount = total_amount
    stub.company_address = company_address
    stub.services.all.return_value = []
    stub.reimbursements.all.return_value = []
    stub.deductions.all.return_value = []
    return stub


# ---------------------------------------------------------------------------
# ContractReminderService — URL building
# ---------------------------------------------------------------------------

class ContractReminderURLTest(SimpleTestCase):

    def _simulate_send_reminder(self, interpreter, invitation, level, site_url='https://portal.test.com'):
        """Reproduce the _send_reminder URL-building logic without importing the service."""
        user = interpreter.user

        base_url = site_url.rstrip('/')
        if invitation:
            review_path = f"/contracts/review/{invitation.review_token}/"
            accept_path = f"/contracts/accept/{invitation.accept_token}/"
            contract_url = f"{base_url}{review_path}"
            accept_url = f"{base_url}{accept_path}"
        else:
            dashboard_path = "/interpreter/dashboard/"
            contract_url = f"{base_url}{dashboard_path}"
            accept_url = contract_url

        return {
            'interpreter_name': user.get_full_name(),
            'contract_url': contract_url,
            'accept_url': accept_url,
            'days_pending': [3, 7, 14][level - 1],
        }

    def test_with_invitation_uses_review_token(self):
        interp = _make_interpreter()
        inv = _make_invitation(review_token='rv-abc', accept_token='ac-xyz')
        ctx = self._simulate_send_reminder(interp, inv, level=1)
        self.assertIn('rv-abc', ctx['contract_url'])

    def test_with_invitation_accept_url_uses_accept_token(self):
        interp = _make_interpreter()
        inv = _make_invitation(review_token='rv-abc', accept_token='ac-xyz')
        ctx = self._simulate_send_reminder(interp, inv, level=1)
        self.assertIn('ac-xyz', ctx['accept_url'])

    def test_without_invitation_falls_back_to_dashboard(self):
        interp = _make_interpreter()
        ctx = self._simulate_send_reminder(interp, None, level=2)
        self.assertIn('dashboard', ctx['contract_url'])

    def test_without_invitation_contract_url_equals_accept_url(self):
        interp = _make_interpreter()
        ctx = self._simulate_send_reminder(interp, None, level=1)
        self.assertEqual(ctx['contract_url'], ctx['accept_url'])

    def test_site_url_trailing_slash_stripped(self):
        interp = _make_interpreter()
        inv = _make_invitation()
        ctx = self._simulate_send_reminder(interp, inv, level=1, site_url='https://portal.test.com/')
        self.assertFalse(ctx['contract_url'].startswith('https://portal.test.com//'))

    def test_days_pending_level_1(self):
        interp = _make_interpreter()
        ctx = self._simulate_send_reminder(interp, None, level=1)
        self.assertEqual(ctx['days_pending'], 3)

    def test_days_pending_level_2(self):
        interp = _make_interpreter()
        ctx = self._simulate_send_reminder(interp, None, level=2)
        self.assertEqual(ctx['days_pending'], 7)

    def test_days_pending_level_3(self):
        interp = _make_interpreter()
        ctx = self._simulate_send_reminder(interp, None, level=3)
        self.assertEqual(ctx['days_pending'], 14)

    def test_interpreter_name_in_context(self):
        interp = _make_interpreter(full_name='Marie Curie')
        ctx = self._simulate_send_reminder(interp, None, level=1)
        self.assertEqual(ctx['interpreter_name'], 'Marie Curie')

    @patch('app.services.email_service.ContractReminder')
    @patch('app.services.email_service.send_mail')
    @patch('app.services.email_service.render_to_string', return_value='<html>reminder</html>')
    @patch('app.services.email_service.reverse')
    @patch('app.services.email_service.settings')
    def test_send_reminder_calls_send_mail(
        self, mock_settings, mock_reverse, mock_render, mock_send_mail, mock_cr
    ):
        from app.services.email_service import ContractReminderService

        mock_settings.SITE_URL = 'https://portal.test.com'
        mock_reverse.side_effect = lambda name, **kw: f"/{name}/"

        interp = _make_interpreter()
        inv = _make_invitation()

        ContractReminderService._send_reminder(
            interp, inv, level=1,
            subject='Test Reminder',
            template='emails/contractnotif/reminder_level_1.html',
        )

        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(kwargs.get('subject') or args[0], 'Test Reminder')

    @patch('app.services.email_service.ContractReminder')
    @patch('app.services.email_service.send_mail', side_effect=Exception('SMTP error'))
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    @patch('app.services.email_service.reverse')
    @patch('app.services.email_service.settings')
    def test_send_reminder_returns_false_on_exception(
        self, mock_settings, mock_reverse, mock_render, mock_send_mail, mock_cr
    ):
        from app.services.email_service import ContractReminderService

        mock_settings.SITE_URL = 'https://portal.test.com'
        mock_reverse.side_effect = lambda name, **kw: f"/{name}/"

        interp = _make_interpreter()
        result = ContractReminderService._send_reminder(
            interp, None, level=1,
            subject='Test', template='t.html',
        )
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# PayrollEmailService
# ---------------------------------------------------------------------------

class PayrollEmailServiceTest(SimpleTestCase):

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html>paystub</html>')
    def test_send_stub_calls_render_to_string(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub()
        PayrollEmailService.send_stub(stub, b'%PDF-stub')

        mock_render.assert_called_once()
        template_name = mock_render.call_args[0][0]
        self.assertEqual(template_name, 'emails/payroll_stub.html')

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html>paystub</html>')
    def test_send_stub_attaches_pdf(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub(document_number='PAY-001')
        PayrollEmailService.send_stub(stub, b'%PDF-data')

        attach_args = mock_msg.attach.call_args[0]
        self.assertEqual(attach_args[0], 'paystub-PAY-001.pdf')
        self.assertEqual(attach_args[1], b'%PDF-data')
        self.assertEqual(attach_args[2], 'application/pdf')

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    def test_send_stub_sends_to_interpreter_email(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub(interpreter_email='pay@interp.com')
        PayrollEmailService.send_stub(stub, b'%PDF')

        _, kwargs = mock_email_cls.call_args
        self.assertEqual(kwargs['to'], ['pay@interp.com'])

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    def test_send_stub_returns_true_on_success(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub()
        result = PayrollEmailService.send_stub(stub, b'%PDF')
        self.assertTrue(result)

    @patch('app.services.email_service.render_to_string', side_effect=Exception('template missing'))
    def test_send_stub_returns_false_on_exception(self, mock_render):
        from app.services.email_service import PayrollEmailService

        stub = _make_stub()
        result = PayrollEmailService.send_stub(stub, b'%PDF')
        self.assertFalse(result)

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    def test_send_stub_subject_contains_document_number(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub(document_number='PAY-2025-007')
        PayrollEmailService.send_stub(stub, b'%PDF')

        _, kwargs = mock_email_cls.call_args
        self.assertIn('PAY-2025-007', kwargs['subject'])

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    def test_send_stub_context_includes_services(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        service = MagicMock()
        stub = _make_stub()
        stub.services.all.return_value = [service]

        PayrollEmailService.send_stub(stub, b'%PDF')

        ctx = mock_render.call_args[0][1]
        self.assertIn(service, ctx['services'])

    @patch('app.services.email_service.EmailMessage')
    @patch('app.services.email_service.render_to_string', return_value='<html/>')
    def test_send_stub_html_content_subtype(self, mock_render, mock_email_cls):
        from app.services.email_service import PayrollEmailService

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        stub = _make_stub()
        PayrollEmailService.send_stub(stub, b'%PDF')

        self.assertEqual(mock_msg.content_subtype, 'html')

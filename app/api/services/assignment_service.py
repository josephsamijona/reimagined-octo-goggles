"""
Standalone service functions for assignment payment management and calendar sync.

Design rules:
- Payment status is ALWAYS controlled manually by the admin.  These functions
  never push a payment beyond PENDING automatically.
- On assignment CONFIRMED  → create InterpreterPayment (status=PENDING)
- On assignment COMPLETED  → create Expense only; leave payment as PENDING
- On assignment CANCELLED  → cancel/reject existing payment + expense
- On assignment CONFIRMED  → push event to company Google Calendar (via FastAPI)
"""
import logging
import uuid

import requests
from django.conf import settings
from django.utils import timezone

from app.models import FinancialTransaction, InterpreterPayment, Expense

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interpreter payment helpers
# ---------------------------------------------------------------------------

def _create_payment(assignment, status, created_by):
    """Create a FinancialTransaction + InterpreterPayment pair.

    Args:
        assignment: Assignment model instance.
        status: Initial payment status string (e.g. 'PENDING', 'PROCESSING').
        created_by: User instance who triggered the action.

    Returns:
        The newly created InterpreterPayment instance.
    """
    transaction = FinancialTransaction.objects.create(
        type='EXPENSE',
        amount=assignment.total_interpreter_payment,
        description=f"Interpreter payment for assignment #{assignment.id}",
        created_by=created_by,
    )
    due_date = timezone.now() + timezone.timedelta(days=14)
    return InterpreterPayment.objects.create(
        transaction=transaction,
        interpreter=assignment.interpreter,
        assignment=assignment,
        amount=assignment.total_interpreter_payment,
        payment_method='ACH',
        status=status,
        scheduled_date=due_date,
        reference_number=f"INT-{assignment.id}-{uuid.uuid4().hex[:6].upper()}",
    )


def create_interpreter_payment(assignment, created_by):
    """Create InterpreterPayment (status=PENDING) when assignment is confirmed.

    Args:
        assignment: Assignment model instance.
        created_by: User instance who triggered the action.

    Returns:
        The newly created InterpreterPayment instance.
    """
    return _create_payment(assignment, 'PENDING', created_by)


def update_interpreter_payment(assignment, new_status, created_by=None):
    """Update (or create if absent) the interpreter payment to *new_status*.

    Aligns with AssignmentAdminMixin.update_interpreter_payment() which also
    creates a new payment when none exists.  This prevents data gaps when the
    admin skips the CONFIRMED step.

    NOTE: new_status should only be set explicitly by admin actions.  The
    automated completion flow must NOT call this — it leaves the payment at
    PENDING so the admin retains full control over the payout lifecycle.

    Args:
        assignment: Assignment model instance.
        new_status: New payment status string (e.g. 'PROCESSING', 'COMPLETED').
        created_by: User instance, used only when creating a new payment.

    Returns:
        The updated or newly created InterpreterPayment instance.
    """
    try:
        payment = assignment.interpreterpayment_set.latest('created_at')
        payment.status = new_status
        payment.save()
        logger.info(
            "Updated payment for assignment %s → %s", assignment.id, new_status
        )
        return payment
    except InterpreterPayment.DoesNotExist:
        logger.info(
            "No payment for assignment %s — creating one with status %s",
            assignment.id, new_status,
        )
        return _create_payment(assignment, new_status, created_by)


def cancel_interpreter_payment(assignment):
    """Cancel the interpreter payment (and its expense) when an assignment is cancelled.

    Does nothing if the payment is already COMPLETED or FAILED.

    Args:
        assignment: Assignment model instance.
    """
    try:
        payment = assignment.interpreterpayment_set.latest('created_at')
        if payment.status not in ['COMPLETED', 'FAILED']:
            payment.status = 'CANCELLED'
            payment.save()
            expense = Expense.objects.filter(transaction=payment.transaction).first()
            if expense and expense.status != 'PAID':
                expense.status = 'REJECTED'
                expense.save()
    except InterpreterPayment.DoesNotExist:
        pass


def create_expense_for_assignment(assignment):
    """Create an Expense record (status=PENDING) when an assignment is completed.

    The associated InterpreterPayment is NOT updated here — the admin handles
    the payment status transition manually.

    Args:
        assignment: Assignment model instance.

    Returns:
        The newly created Expense instance, or None if no payment exists.
    """
    try:
        payment = assignment.interpreterpayment_set.latest('created_at')
        return Expense.objects.create(
            transaction=payment.transaction,
            expense_type='SALARY',
            amount=assignment.total_interpreter_payment,
            description=f"Interpreter payment expense for assignment #{assignment.id}",
            status='PENDING',
            date_incurred=timezone.now(),
        )
    except InterpreterPayment.DoesNotExist:
        logger.error(
            "No interpreter payment found for assignment %s — cannot create expense.",
            assignment.id,
        )
        return None


# ---------------------------------------------------------------------------
# Payment calculation
# ---------------------------------------------------------------------------

def calculate_total_payment(interpreter_rate, start_time, end_time, minimum_hours):
    """Calculate total interpreter payment respecting a minimum billable duration.

    Args:
        interpreter_rate: Decimal or float hourly rate.
        start_time: datetime of assignment start.
        end_time: datetime of assignment end.
        minimum_hours: float minimum billable hours.

    Returns:
        Rounded float total payment amount.
    """
    duration = (end_time - start_time).total_seconds() / 3600
    billable_hours = max(duration, minimum_hours)
    return round(interpreter_rate * billable_hours, 2)


# ---------------------------------------------------------------------------
# Google Calendar sync
# ---------------------------------------------------------------------------

def add_assignment_to_google_calendar(assignment_id: int) -> dict:
    """Push an assignment to the company's Google Calendar via the FastAPI service.

    Calls ``POST /calendar/sync-assignment`` on the FastAPI microservice.  The
    call is fire-and-forget from the assignment lifecycle perspective: a failure
    is logged but never raises an exception so it cannot break the payment or
    status-change flow.

    The FastAPI base URL is read from ``settings.FASTAPI_BASE_URL`` (default:
    ``http://localhost:8001``).

    Args:
        assignment_id: Primary key of the Assignment to sync.

    Returns:
        Dict with ``event_id`` and ``html_link`` on success, empty dict on failure.
    """
    fastapi_url = getattr(settings, 'FASTAPI_BASE_URL', 'http://localhost:8001')
    endpoint = f"{fastapi_url.rstrip('/')}/calendar/sync-assignment"

    try:
        resp = requests.post(
            endpoint,
            json={"assignment_id": assignment_id},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            logger.info(
                "Assignment %s synced to Google Calendar: %s",
                assignment_id, data.get('html_link', ''),
            )
            return data
        logger.warning(
            "Calendar sync returned %s for assignment %s: %s",
            resp.status_code, assignment_id, resp.text[:200],
        )
        return {}
    except requests.RequestException as exc:
        logger.error(
            "Calendar sync failed for assignment %s: %s", assignment_id, exc
        )
        return {}

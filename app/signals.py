# signals.py
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, QuoteRequest, Quote, Assignment, AssignmentNotification

logger = logging.getLogger(__name__)


def _safe_celery_delay(task_func, *args):
    """Wrapper pour appeler .delay() sans crasher si Redis/Celery est down."""
    try:
        task_func.delay(*args)
    except Exception:
        logger.warning(
            "Celery unavailable — skipped task %s(%s)",
            task_func.name if hasattr(task_func, 'name') else task_func.__name__,
            args,
        )


@receiver(post_save, sender=Assignment)
def create_assignment_notification(sender, instance, created, **kwargs):
    if created and instance.interpreter and instance.status == Assignment.Status.PENDING:
        try:
            AssignmentNotification.create_for_new_assignment(instance)
        except Exception:
            logger.exception("Failed to create assignment notification for Assignment #%s", instance.pk)


@receiver(post_save, sender=Quote)
def handle_quote_status_change(sender, instance, created, **kwargs):
    from .tasks import send_quote_status_email
    if instance.status != 'DRAFT':
        if created or instance.status != instance._original_status:
            _safe_celery_delay(send_quote_status_email, instance.id)


@receiver(post_save, sender=Assignment)
def handle_assignment_status_change(sender, instance, created, **kwargs):
    from .tasks import send_assignment_status_email
    if created or instance.status != instance._original_status:
        _safe_celery_delay(send_assignment_status_email, instance.id)


@receiver(post_save, sender=Assignment)
def sync_assignment_to_google_calendar(sender, instance, **kwargs):
    """Sync assignment to Google Calendar after transaction commit (non-blocking)."""
    from django.db import transaction
    from .services.google_calendar import schedule_sync
    pk = instance.pk
    def _on_commit():
        try:
            schedule_sync(pk)
        except Exception:
            logger.exception("Google Calendar sync failed for Assignment #%s", pk)
    transaction.on_commit(_on_commit)


@receiver(post_save, sender=QuoteRequest)
def handle_quote_request_status_change(sender, instance, created, **kwargs):
    from .tasks import send_quote_request_status_email
    if created or instance.status != instance._original_status:
        _safe_celery_delay(send_quote_request_status_email, instance.id)


@receiver(post_save, sender=User)
def send_welcome_email_on_creation(sender, instance, created, **kwargs):
    from .tasks import send_welcome_email
    if created:
        _safe_celery_delay(send_welcome_email, instance.id)

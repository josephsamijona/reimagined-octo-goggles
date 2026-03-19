# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, QuoteRequest, Quote, Assignment, AssignmentNotification
from .tasks import (
    send_welcome_email,
    send_quote_request_status_email,
    send_quote_status_email,
    send_assignment_status_email,
)


@receiver(post_save, sender=Assignment)
def create_assignment_notification(sender, instance, created, **kwargs):
    if created and instance.interpreter and instance.status == Assignment.Status.PENDING:
        AssignmentNotification.create_for_new_assignment(instance)


@receiver(post_save, sender=Quote)
def handle_quote_status_change(sender, instance, created, **kwargs):
    # Ne pas envoyer d'email si le statut est DRAFT
    if instance.status != 'DRAFT':
        if created or instance.status != instance._original_status:
            send_quote_status_email.delay(instance.id)


@receiver(post_save, sender=Assignment)
def handle_assignment_status_change(sender, instance, created, **kwargs):
    if created or instance.status != instance._original_status:
        send_assignment_status_email.delay(instance.id)


@receiver(post_save, sender=QuoteRequest)
def handle_quote_request_status_change(sender, instance, created, **kwargs):
    # Envoyer l'email pour une nouvelle demande ou un changement de statut
    if created or instance.status != instance._original_status:
        send_quote_request_status_email.delay(instance.id)


@receiver(post_save, sender=User)
def send_welcome_email_on_creation(sender, instance, created, **kwargs):
    if created:  # Uniquement lors de la création
        send_welcome_email.delay(instance.id)

from django.contrib import admin
from django.utils import timezone
from django.urls import path
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

import logging
import uuid

from app.utils.timezone import BOSTON_TZ, get_interpreter_timezone, format_local_datetime
from app.api.services.assignment_service import (
    create_interpreter_payment as svc_create_payment,
    cancel_interpreter_payment as svc_cancel_payment,
    create_expense_for_assignment,
    add_assignment_to_google_calendar,
)
import app.services.assignment_email_service as email_svc

logger = logging.getLogger(__name__)

class AssignmentAdminMixin:
    """Mixin for handling all assignment-related administrative tasks."""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'assignment/<path:assignment_token>/accept/',
                self.admin_site.admin_view(self.accept_assignment_view),
                name='assignment-accept',
            ),
            path(
                'assignment/<path:assignment_token>/decline/',
                self.admin_site.admin_view(self.decline_assignment_view),
                name='assignment-decline',
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        """
        Override save_model pour gérer les changements de statut d'assignment, 
        les paiements et les notifications.
        """
        old_status = None
        old_interpreter = None
        
        if change:  # Si c'est une modification
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                old_status = old_obj.status
                old_interpreter = old_obj.interpreter
            except self.model.DoesNotExist:
                pass

        # Sauvegarde du modèle
        super().save_model(request, obj, form, change)

        try:
            # Gestion des nouveaux assignments ou changements d'interprètes
            if obj.interpreter and (not change or old_interpreter != obj.interpreter):
                if obj.status == 'PENDING':
                    self.handle_new_assignment_notification(request, obj)

            # Gestion des changements de statut
            if change and old_status != obj.status:
                # Gestion des paiements selon le changement de statut
                self.handle_status_change(request, obj, old_status)
                # Gestion des notifications email
                self.handle_status_change_notification(request, obj, old_status)

        except Exception as e:
            logger.error(f"Error in save_model: {str(e)}", exc_info=True)
            messages.error(request, _("Error processing changes. Please check the logs."))

    def handle_status_change(self, request, obj, old_status):
        """Gère les changements de statut et délègue au service partagé.

        Règles de paiement :
        - CONFIRMED → crée InterpreterPayment (PENDING) + push Google Calendar
        - COMPLETED → crée seulement l'Expense ; le paiement reste PENDING
                      (l'admin change le statut manuellement)
        - CANCELLED → annule paiement + dépense existants
        """
        try:
            if obj.status == 'CONFIRMED' and old_status != 'CONFIRMED':
                svc_create_payment(obj, request.user)
                add_assignment_to_google_calendar(obj.id)

            elif obj.status == 'COMPLETED' and old_status != 'COMPLETED':
                # Payment stays PENDING — admin controls payout manually
                create_expense_for_assignment(obj)

            elif obj.status == 'CANCELLED' and old_status != 'CANCELLED':
                svc_cancel_payment(obj)

        except Exception as e:
            logger.error(f"Error handling status change: {str(e)}", exc_info=True)
            raise

    def create_interpreter_payment(self, request, assignment, status):
        """
        Crée un nouveau paiement interprète avec sa transaction financière associée.
        Appelé uniquement lors de la confirmation initiale de l'assignment.
        """
        from app.models import InterpreterPayment, FinancialTransaction
        
        # Création de la transaction financière
        transaction = FinancialTransaction.objects.create(
            type='EXPENSE',
            amount=assignment.total_interpreter_payment,
            description=f"Interpreter payment for assignment #{assignment.id}",
            created_by=request.user
        )

        # Date d'échéance = date actuelle + 14 jours
        due_date = timezone.now() + timezone.timedelta(days=14)
        
        # Création du paiement interprète
        InterpreterPayment.objects.create(
            transaction=transaction,
            interpreter=assignment.interpreter,
            assignment=assignment,
            amount=assignment.total_interpreter_payment,
            payment_method='ACH',  # Méthode par défaut
            status=status,
            scheduled_date=due_date,
            reference_number=f"INT-{assignment.id}-{uuid.uuid4().hex[:6].upper()}"
        )

    def update_interpreter_payment(self, request, assignment, new_status):
        """
        Met à jour ou crée un paiement interprète selon le besoin.
        """
        try:
            # Essayer de récupérer le paiement existant
            interpreter_payment = assignment.interpreterpayment_set.latest('created_at')
            interpreter_payment.status = new_status
            interpreter_payment.save()
            logger.info(f"Updated payment for assignment {assignment.id} to status {new_status}")
            return interpreter_payment

        except assignment.interpreterpayment_set.model.DoesNotExist:
            logger.info(f"No payment found for assignment {assignment.id}, creating new one")
            # Si pas de paiement, en créer un nouveau
            from app.models import InterpreterPayment, FinancialTransaction
            
            # Créer la transaction financière
            transaction = FinancialTransaction.objects.create(
                type='EXPENSE',
                amount=assignment.total_interpreter_payment,
                description=f"Interpreter payment for assignment #{assignment.id}",
                created_by=request.user if request else None
            )

            # Créer le paiement
            interpreter_payment = InterpreterPayment.objects.create(
                transaction=transaction,
                interpreter=assignment.interpreter,
                assignment=assignment,
                amount=assignment.total_interpreter_payment,
                payment_method='ACH',
                status=new_status,
                scheduled_date=timezone.now() + timezone.timedelta(days=14),
                reference_number=f"INT-{assignment.id}-{uuid.uuid4().hex[:6].upper()}"
            )
            logger.info(f"Created new payment for assignment {assignment.id}")
            return interpreter_payment

    def create_expense(self, request, assignment):
        """
        Crée une dépense associée au paiement interprète existant.
        Appelé lors de la completion de l'assignment.
        """
        from app.models import Expense
        
        try:
            interpreter_payment = assignment.interpreterpayment_set.latest('created_at')
            
            Expense.objects.create(
                transaction=interpreter_payment.transaction,
                expense_type='SALARY',
                amount=assignment.total_interpreter_payment,
                description=f"Interpreter payment expense for assignment #{assignment.id}",
                status='PENDING',
                date_incurred=timezone.now()
            )
        except assignment.interpreterpayment_set.model.DoesNotExist:
            logger.error(f"No interpreter payment found for assignment {assignment.id}")
            raise

    def cancel_interpreter_payment(self, request, assignment):
        """
        Annule le paiement interprète et la dépense associée si l'assignment est annulé.
        Ne fait rien si le paiement est déjà complété ou a échoué.
        """
        try:
            interpreter_payment = assignment.interpreterpayment_set.latest('created_at')
            if interpreter_payment.status not in ['COMPLETED', 'FAILED']:
                interpreter_payment.status = 'CANCELLED'
                interpreter_payment.save()

                # Annulation de la dépense associée si elle existe et n'est pas payée
                from app.models import Expense
                expense = Expense.objects.filter(transaction=interpreter_payment.transaction).first()
                if expense and expense.status != 'PAID':
                    expense.status = 'REJECTED'
                    expense.save()

        except assignment.interpreterpayment_set.model.DoesNotExist:
            pass  # Pas d'erreur si aucun paiement n'existe

    def handle_new_assignment_notification(self, request, obj):
        """Handle notifications for new assignments — delegates to email service."""
        site_url = f"{request.scheme}://{request.get_host()}"
        if email_svc.send_assignment_email(obj, 'new', site_url=site_url):
            messages.success(request, _("Assignment notification sent successfully."))
        else:
            messages.error(request, _("Error sending assignment notification."))

    def handle_status_change_notification(self, request, obj, old_status):
        """Handle notifications for status changes — delegates to email service."""
        status_email_types = {
            'CONFIRMED': 'confirmed',
            'CANCELLED': 'cancelled',
            'COMPLETED': 'completed',
            'NO_SHOW': 'no_show',
        }
        if obj.status in status_email_types and obj.interpreter:
            email_type = status_email_types[obj.status]
            site_url = f"{request.scheme}://{request.get_host()}"
            if email_svc.send_assignment_email(obj, email_type, site_url=site_url):
                messages.success(request, _("Status change notification sent successfully."))
            else:
                messages.error(request, _("Error sending status change notification."))

    # ------------------------------------------------------------------
    # Thin delegations kept for backward compatibility (admin token views)
    # ------------------------------------------------------------------

    def generate_assignment_token(self, assignment_id, action):
        return email_svc.generate_assignment_token(assignment_id, action)

    def verify_assignment_token(self, token, expected_action):
        return email_svc.verify_assignment_token(token, expected_action)

    def send_assignment_email(self, request, assignment, email_type='new'):
        site_url = f"{request.scheme}://{request.get_host()}"
        return email_svc.send_assignment_email(assignment, email_type, site_url=site_url)

    def log_email_sent(self, assignment, email_type):
        email_svc.log_email_sent(assignment, email_type)

    def accept_assignment_view(self, request, assignment_token):
        """Handle assignment acceptance via admin."""
        assignment_id = self.verify_assignment_token(assignment_token, 'accept')
        if not assignment_id:
            return HttpResponse("Invalid or expired token", status=400)
            
        try:
            assignment = self.model.objects.get(id=assignment_id)
            
            if assignment.status != self.model.Status.PENDING:
                return HttpResponse("Assignment is no longer available", status=400)

            # Update assignment status
            assignment.status = self.model.Status.CONFIRMED
            assignment.save()

            # Envoyer l'email de confirmation
            self.send_assignment_email(request, assignment, 'confirmed')
            
            # Log l'action
            self.log_email_sent(assignment, 'ASSIGNMENT_ACCEPTED')

            return HttpResponse("Assignment accepted successfully.")
            
        except self.model.DoesNotExist:
            return HttpResponse("Assignment not found", status=404)

    def decline_assignment_view(self, request, assignment_token):
        """Handle assignment decline via admin."""
        assignment_id = self.verify_assignment_token(assignment_token, 'decline')
        if not assignment_id:
            return HttpResponse("Invalid or expired token", status=400)
            
        try:
            assignment = self.model.objects.get(id=assignment_id)
            
            if assignment.status != self.model.Status.PENDING:
                return HttpResponse("Assignment is no longer available", status=400)

            interpreter = assignment.interpreter
            
            # Update assignment status + remove interpreter
            assignment.status = self.model.Status.CANCELLED
            assignment.interpreter = None
            assignment.save()

            # Log l'action
            self.log_email_sent(assignment, 'ASSIGNMENT_DECLINED')

            # Envoyer l'email d'annulation
            self.send_assignment_email(request, assignment, 'cancelled')

            return HttpResponse("Assignment declined successfully.")
            
        except self.model.DoesNotExist:
            return HttpResponse("Assignment not found", status=404)
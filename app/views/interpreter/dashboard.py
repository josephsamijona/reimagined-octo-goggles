from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...mixins.assignment_mixins import AssignmentAdminMixin
from ...models import Assignment
from ...utils.contract_helpers import has_signed_contract, get_contract_wizard_link
from ..utils import BOSTON_TZ

@login_required
def dashboard_view(request):
    """
    Vue principale du dashboard.
    Vérifie que l'utilisateur a complété son inscription,
    puis vérifie qu'il possède un profil d'interprète,
    calcule les statistiques et prépare les données des missions.
    """
    # Vérification si l'inscription est complète
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    
    if not hasattr(request.user, 'interpreter_profile'):
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })

    interpreter = request.user.interpreter_profile

    # 1. Vérification si le compte est bloqué manuellement
    if interpreter.is_manually_blocked:
        return render(request, 'interpreter/account_blocked.html', {
            'reason': interpreter.blocked_reason,
            'blocked_at': interpreter.blocked_at,
            'blocked_by': interpreter.blocked_by,
            'support_email': 'support@jhbridgetranslation.com'
        })
        
    # 2. Vérification si le contrat est signé
    if not has_signed_contract(request.user):
        contract_link = get_contract_wizard_link(request.user)
        return render(request, 'interpreter/contract_required.html', {
            'user': request.user,
            'contract_link': contract_link
        })

    try:
        # Calcul des statistiques
        stats = get_interpreter_stats(interpreter)

        # Récupération des missions en attente et confirmées
        pending_assignments = get_pending_assignments(interpreter)
        confirmed_assignments = get_confirmed_assignments(interpreter)

        # Préparation des données pour l'affichage
        pending_data = prepare_assignments_data(request, pending_assignments, 'PENDING')
        confirmed_data = prepare_assignments_data(request, confirmed_assignments, 'CONFIRMED')

        context = {
            'stats': stats,
            'pending_assignments': pending_data,
            'confirmed_assignments': confirmed_data
        }

        return render(request, 'interpreter/int_main.html', context)

    except Exception as e:
        return render(request, 'error.html', {
            'message': f'An error occurred: {str(e)}'
        })


def get_interpreter_stats(interpreter):
    """
    Calcule les statistiques de l'interprète pour la semaine en cours.
    - Gains de la semaine (missions complétées)
    - Nombre de missions en attente
    - Nombre de missions confirmées et futures
    """
    # Obtenir le début et la fin de la semaine courante
    today = timezone.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)

    # Calculer les gains de la semaine
    weekly_earnings = Assignment.objects.filter(
        interpreter=interpreter,
        status='COMPLETED',
        completed_at__range=(start_of_week, end_of_week)
    ).aggregate(total=Sum('total_interpreter_payment'))['total']

    pending_count = Assignment.objects.filter(
        interpreter=interpreter,
        status='PENDING'
    ).count()

    upcoming_count = Assignment.objects.filter(
        interpreter=interpreter,
        status='CONFIRMED',
        start_time__gt=timezone.now()
    ).count()

    return {
        'weekly_earnings': '-' if weekly_earnings is None else round(weekly_earnings, 2),
        'earnings_info': 'Click on Payments for more details',  # Message d'information
        'pending_missions': pending_count,
        'upcoming_missions': upcoming_count
    }


def get_pending_assignments(interpreter):
    """
    Récupère les missions en attente avec les relations nécessaires.
    """
    return Assignment.objects.filter(
        interpreter=interpreter,
        status='PENDING'
    ).select_related(
        'service_type',
        'source_language',
        'target_language'
    ).order_by('start_time')


def get_confirmed_assignments(interpreter):
    """
    Récupère les missions confirmées avec les relations nécessaires.
    """
    return Assignment.objects.filter(
        interpreter=interpreter,
        status='CONFIRMED'
    ).select_related(
        'service_type',
        'source_language',
        'target_language'
    ).order_by('start_time')


def prepare_assignments_data(request, assignments, status_type):
    """
    Prépare les données des missions pour l'affichage.
    Ajoute les URLs d'action, et fournit les informations de date complète.
    """
    mixin = AssignmentAdminMixin()
    assignments_data = []

    for assignment in assignments:
        # Génération des tokens ou URLs d'action selon le type de statut
        action_urls = {}
        if status_type == 'PENDING':
            accept_token = mixin.generate_assignment_token(assignment.id, 'accept')
            decline_token = mixin.generate_assignment_token(assignment.id, 'decline')
            action_urls = {
                'accept': f"/assignments/accept/{accept_token}/",
                'decline': f"/assignments/decline/{decline_token}/"
            }
        elif status_type == 'CONFIRMED':
            action_urls = {
                'complete': f"/assignments/{assignment.id}/complete/"
            }

        # Conversion des heures en fuseau horaire de Boston
        start_time = assignment.start_time.astimezone(BOSTON_TZ)
        end_time = assignment.end_time.astimezone(BOSTON_TZ)

        assignment_data = {
            # Informations principales
            'main_info': {
                'id': assignment.id,
                'client_name': assignment.client.company_name if assignment.client else assignment.client_name,
                'address': f"{assignment.location}, {assignment.city}",
                'languages': f"{assignment.source_language.name} → {assignment.target_language.name}",
                'status': status_type,
                'interpreter_rate': assignment.interpreter_rate,
                # Pour l'affichage de l'heure seule
                'start_time': start_time,
                'end_time': end_time,
                # Pour l'affichage complet (date + heure)
                'start_datetime': start_time,
                'end_datetime': end_time,
                'duration': f"{(end_time - start_time).total_seconds() / 3600:.1f} hours"
            },
            # Informations détaillées
            'detailed_info': {
                'special_requirements': assignment.special_requirements or "None",
                'client_phone': assignment.client_phone or "Not provided",
                'client_email': assignment.client_email or "Not provided",
                'total_amount': assignment.total_interpreter_payment,
                'service_type': assignment.service_type.name,
                'full_address': {
                    'location': assignment.location,
                    'city': assignment.city,
                    'state': assignment.state,
                    'zip_code': assignment.zip_code
                }
            },
            # URLs d'action
            'action_urls': action_urls
        }

        assignments_data.append(assignment_data)

    return assignments_data

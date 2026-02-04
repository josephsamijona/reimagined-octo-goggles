from datetime import timedelta, date, datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ...models import Assignment

@login_required
def calendar_view(request):
    """
    Vue pour afficher le calendrier des rendez-vous de l'interprète
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    # Vérifier si l'utilisateur a un profil d'interprète
    if not hasattr(request.user, 'interpreter_profile'):
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })
        

    interpreter = request.user.interpreter_profile

    # Récupérer le mois actuel ou le mois demandé dans les paramètres
    try:
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
    except ValueError:
        year = timezone.now().year
        month = timezone.now().month

    # Créer les dates de début et fin du mois
    start_date = timezone.datetime(year, month, 1)
    if month == 12:
        end_date = timezone.datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = timezone.datetime(year, month + 1, 1) - timedelta(days=1)

    # Récupérer toutes les missions du mois pour l'interprète
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date__range=[start_date, end_date]
    ).select_related(
        'client', 
        'source_language', 
        'target_language'
    ).order_by('start_time')

    # Récupération des prochaines missions (aujourd'hui et à venir)
    now = timezone.now()
    upcoming_assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__gte=now
    ).select_related(
        'client', 
        'source_language', 
        'target_language'
    ).order_by('start_time')[:5]  # Limite aux 5 prochaines missions

    # Grouper les missions par jour avec leur statut
    assignments_by_date = {}
    for assignment in assignments:
        date_key = assignment.start_time.date()
        if date_key not in assignments_by_date:
            assignments_by_date[date_key] = {
                'missions': [],
                'status_count': {status[0]: 0 for status in Assignment.Status.choices}
            }
        
        # Préparation des informations détaillées pour chaque mission
        mission_details = {
            'id': assignment.id,
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'status': assignment.status,
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'notes': assignment.notes,
            'special_requirements': assignment.special_requirements
        }
        
        assignments_by_date[date_key]['missions'].append(mission_details)
        assignments_by_date[date_key]['status_count'][assignment.status] += 1

    # Préparation des données pour les missions à venir
    upcoming_missions_details = []
    for assignment in upcoming_assignments:
        upcoming_mission = {
            'id': assignment.id,
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'status': assignment.status,
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'can_be_started': assignment.can_be_started(),
            'can_be_completed': assignment.can_be_completed(),
            'can_be_cancelled': assignment.can_be_cancelled()
        }
        upcoming_missions_details.append(upcoming_mission)

    # Récupérer les missions du jour actuel
    today = timezone.now().date()
    todays_assignments = []
    
    # Filtrer les missions pour aujourd'hui
    if today in assignments_by_date:
        todays_assignments = assignments_by_date[today]['missions']

    # Créer le contexte avec toutes les données nécessaires
    context = {
        'current_year': year,
        'current_month': month,
        'assignments_by_date': assignments_by_date,
        'upcoming_missions': upcoming_missions_details,
        'todays_assignments': todays_assignments,  # Ajout des missions du jour
        'statuses': Assignment.Status.choices,
        'today': today,
        'interpreter': interpreter,
        'current_time': timezone.now(),
        'has_appointments_today': len(todays_assignments) > 0  # Indicateur pour savoir s'il y a des missions aujourd'hui
    }

    return render(request, 'interpreter/int_calend.html', context)


@login_required
@require_http_methods(["GET"])
def calendar_data_api(request, year, month):
    """
    API pour récupérer les données du calendrier pour un mois spécifique
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    
    # Créer les dates de début et fin du mois
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Récupérer toutes les missions du mois
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date__range=[start_date, end_date - timedelta(days=1)]
    ).values('start_time__date', 'status')

    # Organiser les données par date
    dates_data = {}
    for assignment in assignments:
        date_str = assignment['start_time__date'].isoformat()
        if date_str not in dates_data:
            dates_data[date_str] = {
                'has_missions': True,
                'mission_count': 1,
                'status_summary': {status[0]: 0 for status in Assignment.Status.choices}
            }
        else:
            dates_data[date_str]['mission_count'] += 1
        dates_data[date_str]['status_summary'][assignment['status']] += 1

    return JsonResponse({
        'dates': dates_data
    })

@login_required
@require_http_methods(["GET"])
def daily_missions_api(request, date_str):
    """
    API pour récupérer les missions d'une journée spécifique
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    
    try:
        # Convertir la date string en objet date
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Récupérer les missions du jour
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date=target_date
    ).select_related(
        'client',
        'source_language',
        'target_language'
    )

    missions_data = []
    for assignment in assignments:
        missions_data.append({
            'id': assignment.id,
            'start_time': assignment.start_time.isoformat(),
            'end_time': assignment.end_time.isoformat(),
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'status': assignment.status,
            'can_be_started': assignment.can_be_started(),
            'can_be_completed': assignment.can_be_completed(),
            'can_be_cancelled': assignment.can_be_cancelled(),
            'notes': assignment.notes,
            'special_requirements': assignment.special_requirements
        })

    return JsonResponse({
        'date': date_str,
        'missions': missions_data
    })

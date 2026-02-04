import json
import traceback
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncYear, ExtractMonth, ExtractYear, ExtractDay
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView, ListView
import logging

from ..models import Payment, Assignment
from .utils import calculate_trend, calculate_percentage

logger = logging.getLogger(__name__)

class TranslatorEarningsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/earnings.html'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile
        now = timezone.now()

        # Statistiques générales
        all_payments = Payment.objects.filter(
            assignment__interpreter=interpreter,
            payment_type='INTERPRETER_PAYMENT'
        )

        # Statistiques du mois en cours
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_payments = all_payments.filter(payment_date__gte=current_month_start)

        context['current_month'] = {
            'earnings': current_month_payments.filter(status='COMPLETED').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'pending': current_month_payments.filter(status='PENDING').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'assignments': current_month_payments.count(),
        }

        # Statistiques des 12 derniers mois
        twelve_months_ago = now - timedelta(days=365)
        monthly_earnings = all_payments.filter(
            payment_date__gte=twelve_months_ago,
            status='COMPLETED'
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')

        context['monthly_earnings'] = monthly_earnings

        # Statistiques annuelles
        yearly_earnings = all_payments.filter(
            status='COMPLETED'
        ).annotate(
            year=TruncYear('payment_date')
        ).values('year').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-year')

        context['yearly_earnings'] = yearly_earnings

        # Paiements récents
        context['recent_payments'] = all_payments.select_related(
            'assignment'
        ).order_by('-payment_date')[:10]

        # Paiements en attente
        context['pending_payments'] = all_payments.filter(
            status='PENDING'
        ).select_related('assignment').order_by('-payment_date')

        # Statistiques globales
        context['total_stats'] = {
            'lifetime_earnings': all_payments.filter(status='COMPLETED').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_assignments': all_payments.filter(status='COMPLETED').count(),
            'pending_amount': all_payments.filter(status='PENDING').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'average_payment': all_payments.filter(
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00') / (
                all_payments.filter(status='COMPLETED').count() or 1
            )
        }

        # Liste des années pour le filtre
        context['years'] = yearly_earnings.values_list('year', flat=True)

        return context



@require_GET
def get_earnings_data(request, year=None):
    """Vue API pour obtenir les données des gains pour les graphiques"""
    interpreter = request.user.interpreter_profile
    payments = Payment.objects.filter(
        assignment__interpreter=interpreter,
        payment_type='INTERPRETER_PAYMENT'
    )

    if year:
        payments = payments.filter(payment_date__year=year)

    # Données mensuelles
    monthly_data = payments.filter(
        status='COMPLETED'
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')

    # Formatter les données pour les graphiques
    chart_data = {
        'labels': [],
        'earnings': [],
        'assignments': []
    }

    for data in monthly_data:
        chart_data['labels'].append(data['month'].strftime('%B %Y'))
        chart_data['earnings'].append(float(data['total']))
        chart_data['assignments'].append(data['count'])

    return JsonResponse(chart_data)

def appointments_view(request):
    """
    Vue pour afficher la liste des rendez-vous
    """
    return render(request, 'interpreter/appointment.html')

@login_required
def stats_view(request):
    """
    Vue pour afficher les statistiques du dashboard de l'interprète
    """
    logger.info(f"Accessing stats view for user: {request.user.username}")

    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    # Vérifier si l'utilisateur a un profil d'interprète
    if not hasattr(request.user, 'interpreter_profile'):
        logger.error(f"User {request.user.username} does not have interpreter profile")
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })

    # Récupérer l'interprète connecté
    interpreter = request.user.interpreter_profile
    logger.info(f"Retrieved interpreter profile for user: {interpreter}")
    
    try:
        # Définir la période (par défaut le mois en cours)
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        
        logger.info(f"Calculating stats for period: {start_of_month} to {today}")
        
        # Requêtes pour le mois en cours
        current_month_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__gte=start_of_month,
            start_time__lte=today
        )
        
        # Requêtes pour le mois précédent
        last_month_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__gte=last_month_start,
            start_time__lt=start_of_month
        )
        
        # Calcul des statistiques du mois en cours
        current_earnings = current_month_assignments.filter(
            status='COMPLETED'
        ).aggregate(
            total=Sum('total_interpreter_payment')
        )['total'] or Decimal('0')
        
        # Calcul des heures totales actuelles
        completed_assignments = current_month_assignments.filter(status='COMPLETED')
        total_hours = sum(
            (assignment.end_time - assignment.start_time).total_seconds() / 3600
            for assignment in completed_assignments
        )
        
        # Calcul des heures du mois précédent
        last_month_completed = last_month_assignments.filter(status='COMPLETED')
        last_month_hours = sum(
            (assignment.end_time - assignment.start_time).total_seconds() / 3600
            for assignment in last_month_completed
        )
        
        # Statistiques du mois précédent
        last_month_earnings = last_month_assignments.filter(
            status='COMPLETED'
        ).aggregate(
            total=Sum('total_interpreter_payment')
        )['total'] or Decimal('0')
        
        last_month_stats = last_month_assignments.aggregate(
            completed=Count('id', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status='CANCELLED')),
            no_show=Count('id', filter=Q(status='NO_SHOW'))
        )
        
        # Calcul des données pour les graphiques
        earnings_by_period = current_month_assignments.filter(
            status='COMPLETED'
        ).annotate(
            month=ExtractMonth('start_time'),
            year=ExtractYear('start_time')
        ).values('month', 'year').annotate(
            amount=Sum('total_interpreter_payment')
        ).order_by('year', 'month')

        # Préparation des données pour les graphiques
        earnings_data = [
            {
                'month': f"{item['year']}-{item['month']}",
                'amount': float(item['amount'])
            }
            for item in earnings_by_period
        ]
        
        # Statistiques des missions actuelles
        mission_stats = current_month_assignments.aggregate(
            completed=Count('id', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status='CANCELLED')),
            no_show=Count('id', filter=Q(status='NO_SHOW'))
        )
        
        # Distribution des langues
        languages_distribution = current_month_assignments.filter(
            status='COMPLETED'
        ).values(
            'target_language__name'
        ).annotate(
            value=Count('id')
        ).order_by('-value')
        
        # Répartition des heures par jour avec gestion des erreurs
        hours_by_day = []
        days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for assignment in completed_assignments:
            day_index = assignment.start_time.weekday()
            duration = (assignment.end_time - assignment.start_time).total_seconds() / 3600
            
            # Chercher si le jour existe déjà dans hours_by_day
            day_entry = next(
                (item for item in hours_by_day if item['day'] == days_of_week[day_index]), 
                None
            )
            
            if day_entry:
                day_entry['hours'] += duration
            else:
                hours_by_day.append({
                    'day': days_of_week[day_index],
                    'hours': duration
                })
        
        # Trier les jours dans l'ordre
        hours_by_day.sort(key=lambda x: days_of_week.index(x['day']))

        # Remplir les jours manquants avec 0 heures
        existing_days = [entry['day'] for entry in hours_by_day]
        for day in days_of_week:
            if day not in existing_days:
                hours_by_day.append({'day': day, 'hours': 0})
        
        hours_by_day.sort(key=lambda x: days_of_week.index(x['day']))

        # Calcul des tendances
        earnings_trend = calculate_trend(current_earnings, last_month_earnings)
        hours_trend = calculate_trend(total_hours, last_month_hours)
        mission_trend = calculate_trend(
            mission_stats['completed'],
            last_month_stats.get('completed', 0)
        )

        context = {
            'total_earnings': current_earnings,
            'total_hours': round(total_hours, 1),
            'completed_missions': mission_stats['completed'],
            'earnings_trend': earnings_trend,
            'earnings_trend_abs': abs(earnings_trend),
            'hours_trend': hours_trend,
            'hours_trend_abs': abs(hours_trend),
            'mission_trend': mission_trend,
            'mission_trend_abs': abs(mission_trend),
            'mission_stats': {
                'completed_rate': calculate_percentage(mission_stats['completed'], sum(mission_stats.values())),
                'cancelled_rate': calculate_percentage(mission_stats['cancelled'], sum(mission_stats.values())),
                'no_show_rate': calculate_percentage(mission_stats['no_show'], sum(mission_stats.values())),
            },
            'earnings_data': json.dumps(earnings_data),
            'languages_data': json.dumps(list(languages_distribution)),
            'hours_data': json.dumps(hours_by_day),
        }
        
        logger.info("Successfully prepared context for template")
        return render(request, 'interpreter/stats.html', context)
        
    except Exception as e:
        logger.error(f"Error in stats_view: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return render(request, 'error.html', {
            'message': f'An error occurred while loading statistics: {str(e)}'
        })

    
def earnings_data_api(request, period):
    """
    API pour récupérer les données de gains selon la période
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    today = timezone.now()

    try:
        if period == 'week':
            start_date = today - timedelta(days=7)
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__gte=start_date,
                status='COMPLETED'
            ).annotate(
                day=ExtractDay('start_time')
            ).values('day').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('day')

            data = [
                {
                    'day': (start_date + timedelta(days=i)).strftime('%a'),
                    'amount': 0
                } for i in range(7)
            ]

            for entry in assignments:
                day_index = (entry['day'] - start_date.day) % 7
                if 0 <= day_index < 7:
                    data[day_index]['amount'] = float(entry['amount'])

        elif period == 'month':
            start_date = today.replace(day=1)
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__year=today.year,
                start_time__month=today.month,
                status='COMPLETED'
            ).annotate(
                day=ExtractDay('start_time')
            ).values('day').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('day')

            data = [
                {
                    'day': str(i),
                    'amount': 0
                } for i in range(1, 32)
            ]

            for entry in assignments:
                if 1 <= entry['day'] <= 31:
                    data[entry['day']-1]['amount'] = float(entry['amount'])

        else:  # year
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__year=today.year,
                status='COMPLETED'
            ).annotate(
                month=ExtractMonth('start_time')
            ).values('month').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('month')

            data = [
                {
                    'month': (today.replace(month=i, day=1)).strftime('%b'),
                    'amount': 0
                } for i in range(1, 13)
            ]

            for entry in assignments:
                if 1 <= entry['month'] <= 12:
                    data[entry['month']-1]['amount'] = float(entry['amount'])

        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error(f"Error in earnings_data_api: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
    
    
class PaymentListView(ListView):
    model = Assignment
    template_name = 'interpreter/payment_list.html'
    context_object_name = 'assignments'
    
    
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has interpreter profile before proceeding"""
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
            return render(request, 'complete_registration.html', {
            'user': request.user
        })
        if not hasattr(request.user, 'interpreter_profile'):
            return render(request, 'error.html', {
                'message': 'Access denied. Interpreter profile required.'
            })
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Return assignments completed by the current interpreter"""
        # Get interpreter profile
        interpreter = self.request.user.interpreter_profile
        
        return Assignment.objects.filter(
            interpreter=interpreter,
            # Only show completed assignments
            status=Assignment.Status.COMPLETED
        ).order_by('-start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get interpreter profile
        interpreter = self.request.user.interpreter_profile
            
        # Get all completed assignments for the interpreter
        completed_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            status=Assignment.Status.COMPLETED
        )
        
        # Calculate date ranges
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Format date strings
        current_month_name = now.strftime('%B %Y')
        week_start_str = week_start.strftime('%b %d')
        week_end_str = week_end.strftime('%b %d, %Y')
        week_date_range = f"{week_start_str} - {week_end_str}"
        
        # This week's revenue
        weekly_revenue = completed_assignments.filter(
            start_time__gte=week_start
        ).aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # This month's revenue
        monthly_revenue = completed_assignments.filter(
            start_time__gte=month_start
        ).aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # Total revenue
        total_revenue = completed_assignments.aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # Add revenue data to context
        context['weekly_revenue'] = weekly_revenue
        context['monthly_revenue'] = monthly_revenue
        context['total_revenue'] = total_revenue
        
        # Add date information
        context['current_month'] = current_month_name
        context['week_date_range'] = week_date_range
        
        # Payment statistics
        context['paid_count'] = completed_assignments.filter(is_paid=True).count()
        context['unpaid_count'] = completed_assignments.filter(
            Q(is_paid=False) | Q(is_paid=None)
        ).count()
        
        return context

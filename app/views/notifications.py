from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from ..models import Notification

class NotificationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Notification
    template_name = 'trad/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 15

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Grouper les notifications par catégorie
        context['unread_notifications'] = self.get_queryset().filter(read=False)
        context['quote_notifications'] = self.get_queryset().filter(
            Q(type='QUOTE_REQUEST') | Q(type='QUOTE_READY')
        )
        context['assignment_notifications'] = self.get_queryset().filter(
            Q(type='ASSIGNMENT_OFFER') | Q(type='ASSIGNMENT_REMINDER')
        )
        context['payment_notifications'] = self.get_queryset().filter(
            type='PAYMENT_RECEIVED'
        )
        context['system_notifications'] = self.get_queryset().filter(
            type='SYSTEM'
        )
        
        return context

@require_POST
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@require_POST
def mark_all_notifications_as_read(request):
    Notification.objects.filter(
        recipient=request.user,
        read=False
    ).update(read=True)
    return JsonResponse({'status': 'success'})

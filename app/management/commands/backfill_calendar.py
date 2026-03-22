"""
Management command: backfill Google Calendar events for existing assignments.

Usage:
    python manage.py backfill_calendar
    python manage.py backfill_calendar --batch-size 25
    python manage.py backfill_calendar --status CONFIRMED PENDING

This enqueues the Celery task `bulk_backfill_calendar` which processes
assignments in batches, staggering requests to respect the Google Calendar
API rate limit (~10 req/sec).

Prerequisites:
    - Celery worker running: celery -A config worker -l info
    - GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_CALENDAR_ID must be set
    - The service account must have "Make changes to events" on the calendar
"""
from django.core.management.base import BaseCommand

from app.models import Assignment


class Command(BaseCommand):
    help = 'Backfill Google Calendar events for all unsynced assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=50,
            help='Assignments per Celery task batch (default: 50)',
        )
        parser.add_argument(
            '--status', nargs='+',
            choices=['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'],
            default=['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'],
            help='Filter by assignment status (default: all active)',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-sync even assignments that are already marked SYNCED',
        )

    def handle(self, *args, **options):
        from app.tasks_calendar import bulk_backfill_calendar

        batch_size = options['batch_size']
        statuses = options['status']
        force = options['force']

        qs = Assignment.objects.filter(status__in=statuses)
        if not force:
            qs = qs.exclude(gcal_sync_status=Assignment.GCalSyncStatus.SYNCED)

        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to sync — all assignments already synced.'))
            return

        self.stdout.write(
            f'Queuing backfill for {total} assignments '
            f'(batch_size={batch_size}, statuses={statuses}, force={force})'
        )

        # Enqueue the first batch; it chains itself for subsequent batches
        bulk_backfill_calendar.delay(batch_size=batch_size, offset=0)

        self.stdout.write(self.style.SUCCESS(
            f'Backfill task enqueued. Monitor progress in Celery logs.\n'
            f'Estimated tasks: {(total // batch_size) + 1} batches × up to {batch_size} assignments each.'
        ))

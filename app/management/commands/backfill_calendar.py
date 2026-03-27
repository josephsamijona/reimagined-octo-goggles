"""
Management command: backfill Google Calendar events for existing assignments.

Runs synchronously (no Celery needed). Creates calendar events for all
assignments from a given start date to today that haven't been synced yet.

Usage:
    python manage.py backfill_calendar
    python manage.py backfill_calendar --since 2025-02-01
    python manage.py backfill_calendar --force
    python manage.py backfill_calendar --dry-run

Prerequisites:
    - GOOGLE_SERVICE_ACCOUNT_JSON_B64 (or _JSON) and GOOGLE_CALENDAR_ID in .env
    - The service account must have "Make changes to events" on the calendar
"""
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import Assignment
from app.services.google_calendar import (
    _get_service,
    _build_event_body,
    _STATUS_COLOR,
    _TERMINAL_STATUSES,
)


class Command(BaseCommand):
    help = 'Backfill Google Calendar events for assignments (no Celery needed)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--since',
            type=str,
            default='2026-02-01',
            help='Start date in YYYY-MM-DD format (default: 2026-02-01)',
        )
        parser.add_argument(
            '--status',
            nargs='+',
            choices=['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'],
            default=['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'],
            help='Filter by assignment status (default: all active)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-sync even assignments already marked SYNCED',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without calling Google API',
        )

    def handle(self, *args, **options):
        from datetime import datetime

        since_str = options['since']
        statuses = options['status']
        force = options['force']
        dry_run = options['dry_run']

        try:
            since_date = datetime.strptime(since_str, '%Y-%m-%d')
        except ValueError:
            self.stderr.write(self.style.ERROR(f'Invalid date format: {since_str}. Use YYYY-MM-DD.'))
            return

        # Check Google Calendar service
        if not dry_run:
            service, calendar_id = _get_service()
            if service is None:
                self.stderr.write(self.style.ERROR(
                    'Google Calendar service not configured. '
                    'Check GOOGLE_SERVICE_ACCOUNT_JSON_B64 and GOOGLE_CALENDAR_ID in .env'
                ))
                return
        else:
            service, calendar_id = None, None

        # Query assignments
        qs = (
            Assignment.objects
            .select_related(
                'client', 'client__user',
                'interpreter', 'interpreter__user',
                'service_type', 'source_language', 'target_language',
            )
            .filter(
                status__in=statuses,
                start_time__date__gte=since_date,
            )
            .exclude(status__in=list(_TERMINAL_STATUSES))
            .order_by('start_time')
        )

        if not force:
            qs = qs.exclude(gcal_sync_status=Assignment.GCalSyncStatus.SYNCED)

        assignments = list(qs)
        total = len(assignments)

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to sync.'))
            return

        self.stdout.write(
            f'Found {total} assignments to sync '
            f'(since={since_str}, statuses={statuses}, force={force})'
        )

        if dry_run:
            for a in assignments:
                self.stdout.write(
                    f'  [DRY RUN] #{a.pk} — {a.status} — '
                    f'{a.start_time:%Y-%m-%d %H:%M} — '
                    f'{a.service_type} — '
                    f'gcal_status={a.gcal_sync_status}'
                )
            self.stdout.write(self.style.SUCCESS(f'\nDry run complete. {total} assignments would be synced.'))
            return

        # Sync each assignment
        created = 0
        updated = 0
        failed = 0

        for i, assignment in enumerate(assignments, 1):
            try:
                body = _build_event_body(assignment)

                if assignment.gcal_event_id and not force:
                    # Update existing event
                    try:
                        service.events().update(
                            calendarId=calendar_id,
                            eventId=assignment.gcal_event_id,
                            body=body,
                            sendUpdates='none',
                        ).execute()
                        updated += 1
                        self._log_ok(i, total, assignment, 'updated')
                    except Exception as exc:
                        if _is_not_found(exc):
                            # Event was deleted, re-create
                            event = self._create_event(service, calendar_id, assignment, body)
                            created += 1
                            self._log_ok(i, total, assignment, f're-created ({event.get("id", "?")})')
                        else:
                            raise
                else:
                    # Create new event
                    event = self._create_event(service, calendar_id, assignment, body)
                    created += 1
                    self._log_ok(i, total, assignment, f'created ({event.get("id", "?")})')

                # Rate-limit: ~5 requests/sec to stay well under Google's 10/sec
                time.sleep(0.2)

            except Exception as e:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(f'  [{i}/{total}] #{assignment.pk} — FAILED: {e}')
                )
                Assignment.objects.filter(pk=assignment.pk).update(
                    gcal_sync_status='FAILED',
                )
                # Back off on errors
                time.sleep(1)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done! Created: {created}, Updated: {updated}, Failed: {failed}'
        ))

    def _create_event(self, service, calendar_id, assignment, body):
        """Create a new Google Calendar event and update the DB."""
        event = service.events().insert(
            calendarId=calendar_id,
            body=body,
            sendUpdates='none',
        ).execute()

        event_id = event.get('id', '')
        Assignment.objects.filter(pk=assignment.pk).update(
            gcal_event_id=event_id,
            gcal_sync_status='SYNCED',
            gcal_synced_at=timezone.now(),
        )
        return event

    def _log_ok(self, i, total, assignment, action):
        self.stdout.write(
            f'  [{i}/{total}] #{assignment.pk} — {action} — '
            f'{assignment.status} — {assignment.start_time:%Y-%m-%d %H:%M}'
        )


def _is_not_found(exc):
    try:
        from googleapiclient.errors import HttpError
        return isinstance(exc, HttpError) and exc.resp.status == 404
    except ImportError:
        return False

"""
Celery tasks for Google Calendar synchronization.

All calendar I/O is offloaded here so Django request/response cycles
are never blocked by network calls to the Google Calendar API.

Queue: 'calendar'  (configure in config/celery.py if separate worker desired)
Retry policy:
  - rate_limited  → exponential back-off (60s, 120s, 240s, 480s, 960s)
  - unknown error → linear back-off (60s each)
  - permission    → NO retry; ops must fix credentials
  - not_found     → NO retry; assignment deleted or bad ID
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
    name='app.tasks_calendar.sync_assignment_to_calendar',
)
def sync_assignment_to_calendar(self, assignment_id: int):
    """
    Push or update one assignment's Google Calendar event.

    Triggered after any status-changing action on an assignment:
    confirm, start, complete, cancel, no_show, update.
    Also called manually via the sync-calendar viewset action.

    Retry logic:
    - 'rate_limited': exponential back-off capped at attempt 5
    - 'permission':   log critical, do NOT retry (misconfiguration)
    - 'not_found':    log warning, do NOT retry
    - 'unknown':      linear 60s retry
    """
    from app.api.services.calendar_service import sync_assignment

    try:
        result = sync_assignment(assignment_id)
    except Exception as exc:
        logger.error(
            'Unexpected exception in sync_assignment_to_calendar #%s: %s',
            assignment_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60)

    if result.get('ok'):
        logger.info('Calendar sync succeeded for assignment #%s', assignment_id)
        return result

    error = result.get('error', 'unknown')

    if error == 'permission':
        logger.critical(
            'Google Calendar permission error for assignment #%s — '
            'check GOOGLE_SERVICE_ACCOUNT_JSON and calendar sharing settings. '
            'NOT retrying.',
            assignment_id,
        )
        return result  # Do not retry — ops must fix config

    if error == 'not_found':
        logger.warning('Assignment #%s not found — skipping calendar sync', assignment_id)
        return result  # Do not retry

    if error == 'not_configured':
        logger.warning('Google Calendar not configured — skipping sync for assignment #%s', assignment_id)
        return result  # Do not retry

    if error == 'rate_limited':
        countdown = 60 * (2 ** self.request.retries)
        logger.warning(
            'Rate limited by Google Calendar for assignment #%s — retry in %ss',
            assignment_id, countdown,
        )
        raise self.retry(countdown=countdown)

    # Unknown error — linear retry
    logger.error(
        'Calendar sync failed (unknown) for assignment #%s — retry %s/%s',
        assignment_id, self.request.retries + 1, self.max_retries,
    )
    raise self.retry(countdown=60)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    name='app.tasks_calendar.bulk_backfill_calendar',
)
def bulk_backfill_calendar(self, batch_size: int = 50, offset: int = 0):
    """
    Backfill Google Calendar events for all existing assignments.

    Processes assignments in batches of `batch_size`, starting at `offset`.
    Enqueues a follow-up task for the next batch so the worker is never
    monopolised by a single long-running task.

    Triggered by management command: python manage.py backfill_calendar

    Args:
        batch_size: How many assignments to process per task invocation.
        offset: Starting row offset (for batch chaining).
    """
    from app.models import Assignment

    active_statuses = [
        Assignment.Status.PENDING,
        Assignment.Status.CONFIRMED,
        Assignment.Status.IN_PROGRESS,
        Assignment.Status.COMPLETED,
    ]

    batch = list(
        Assignment.objects
        .filter(status__in=active_statuses)
        .exclude(gcal_sync_status=Assignment.GCalSyncStatus.SYNCED)
        .order_by('id')
        [offset:offset + batch_size]
    )

    if not batch:
        logger.info('bulk_backfill_calendar: all assignments processed (offset=%s)', offset)
        return {'done': True, 'total_processed': offset}

    queued = 0
    for assignment in batch:
        sync_assignment_to_calendar.apply_async(
            args=[assignment.id],
            countdown=queued * 0.2,  # stagger: 200ms between each to respect rate limits
        )
        queued += 1

    logger.info(
        'bulk_backfill_calendar: queued %s assignments (offset %s–%s)',
        queued, offset, offset + queued,
    )

    # Chain next batch
    bulk_backfill_calendar.apply_async(
        kwargs={'batch_size': batch_size, 'offset': offset + batch_size},
        countdown=10,  # give the current batch a head start
    )

    return {'queued': queued, 'next_offset': offset + batch_size}

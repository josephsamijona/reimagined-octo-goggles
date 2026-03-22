I now have sufficient knowledge of the codebase to write a complete, accurate implementation plan. The task asks me to write it to a file, but I am in READ-ONLY mode. I will produce the full document content here as my output, clearly noting that the user must save it themselves since this is a planning-only task.

---

# JHBridge Platform — Ultra-Detailed Implementation Plan

**Target file:** `c:\Users\dace\Desktop\workspace\Jhventure\jhbridge\codebase\legacy\legacy\IMPLEMENTATION_PLAN.md`

Note: This is a read-only planning session. The document content below is complete and ready to be saved to the target file. Copy the markdown below and write it to `IMPLEMENTATION_PLAN.md`.

---

```markdown
# JHBridge Platform — Ultra-Detailed Implementation Plan

> **Status:** Planning document — v1.0  
> **Date:** 2026-03-22  
> **Scope:** Three initiatives: Google Calendar Full Sync, Hiring Module, Finance & Accounting Module  
> **Stack:** Django 5.1.4 · DRF · SimpleJWT · Celery + Redis · React (Vite + shadcn/ui + Tailwind v4) · S3 (primary storage) · MySQL

---

## Table of Contents

1. [Shared Conventions](#0-shared-conventions)
2. [Initiative 1 — Google Calendar Full Sync](#initiative-1--google-calendar-full-sync)
3. [Initiative 2 — Hiring Module](#initiative-2--hiring-module)
4. [Initiative 3 — Finance & Accounting Module](#initiative-3--finance--accounting-module)

---

## 0. Shared Conventions

### Storage Rule (non-negotiable)
S3 is the **primary store** for every file (PDFs, signatures, contracts, receipts, resumes). Google Drive is an **export/sharing destination only** — it receives copies, never originals. The `DriveExport` model (defined in Initiative 3) is the canonical index of all pushed copies.

### Code Organisation Rules
- New service files live at `app/api/services/<name>_service.py`
- New models go in `app/models/<domain>.py` and must be re-exported through `app/models/__init__.py`
- New viewsets register on the existing `router` in `app/api/urls.py`
- New Celery tasks go in a domain-scoped file: `app/tasks_<domain>.py`, imported by `config/celery.py` auto-discovery
- New migrations: `python manage.py makemigrations app` — never hand-edit existing migrations
- Frontend service files: `adminfrontend/src/services/<name>Service.js`
- Frontend module components: `adminfrontend/src/components/modules/<Name>Module.jsx`
- All API endpoints follow the `/api/v1/` prefix established in `config/urls.py`

---

## Initiative 1 — Google Calendar Full Sync

### 1.1 Overview and Motivation

The current implementation calls a FastAPI microservice (`services/calendar_sync/`) synchronously inside the Django request/response cycle via `requests.post()` in `app/api/services/assignment_service.py → add_assignment_to_google_calendar()`. This has three critical problems:

1. **Synchronous network call** blocks the Django worker thread for up to 10 seconds on timeout
2. **OAuth2 user-flow credentials** (`InstalledAppFlow`) are unsuitable for server-to-server automation — they require interactive browser login and produce tokens that expire without a refresh flow
3. **No retry logic** — a calendar API failure silently drops the event with no recovery path

The replacement uses a **Google service account** with domain-wide delegation, calls the Calendar API directly from Django via `google-api-python-client`, and offloads all network I/O to **Celery tasks** so the HTTP response is never delayed.

### 1.2 Required pip Dependencies

Add the following to `requirements.txt`:

```
google-api-python-client>=2.100.0
google-auth>=2.23.0
google-auth-httplib2>=0.1.1
```

These replace the OAuth2 user-flow packages (`google-auth-oauthlib`, `InstalledAppFlow`). The `googleapiclient.discovery` import pattern already used in `services/calendar_sync/client.py` is reused — only the credential mechanism changes.

### 1.3 Required Environment Variables

Add to `.env` and Railway environment configuration:

| Variable | Description | Example |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON content of the service account key file, base64-encoded or raw JSON string | `{"type":"service_account","project_id":...}` |
| `GOOGLE_CALENDAR_ID` | The calendar ID to write to (company calendar) | `jhbridge@group.calendar.google.com` |
| `GOOGLE_CALENDAR_TIMEZONE` | Default fallback timezone for events | `America/New_York` |

**Do not** add a file path — store the JSON content directly in the env var. On Railway, paste the raw JSON as the env var value. In `config/settings.py`, parse it with `json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])`.

### 1.4 Google Service Account Setup (Step-by-Step)

1. Open Google Cloud Console → IAM & Admin → Service Accounts
2. Create a new service account: `jhbridge-calendar-sync@<project>.iam.gserviceaccount.com`
3. Grant it no project-level IAM roles (it only needs Calendar access)
4. Create a JSON key → download → copy the full JSON content
5. Set `GOOGLE_SERVICE_ACCOUNT_JSON` env var to the JSON content
6. Open Google Calendar in a browser, go to the company/operations calendar → Settings → Share with specific people
7. Add the service account email with **"Make changes to events"** permission
8. Set `GOOGLE_CALENDAR_ID` to the calendar's ID (found in Calendar Settings → Integrate calendar)

No domain-wide delegation is needed unless interpreters' personal Google calendars are also targeted (not in scope for this initiative).

### 1.5 Assignment Model Changes

**File:** `app/models/services.py` → `Assignment` class

Add three fields:

| Field | Type | Purpose |
|---|---|---|
| `gcal_event_id` | `CharField(max_length=255, blank=True, null=True)` | Google Calendar event ID returned by API on create/update |
| `gcal_sync_status` | `CharField(max_length=20, choices=SyncStatus.choices, default='PENDING')` | Current sync state |
| `gcal_synced_at` | `DateTimeField(null=True, blank=True)` | Timestamp of last successful sync |

Add a nested `SyncStatus` choices class to `Assignment`:

```
class SyncStatus(models.TextChoices):
    PENDING   = 'PENDING',   'Pending'
    SYNCED    = 'SYNCED',    'Synced'
    FAILED    = 'FAILED',    'Failed'
    SKIPPED   = 'SKIPPED',   'Skipped'   # e.g. cancelled before sync
    DELETED   = 'DELETED',   'Deleted'   # event was removed from calendar
```

Generate and apply migration after adding these fields.

**Why nullable `gcal_event_id`:** Assignments created before the migration or during calendar API outages will have no event ID. The sync task handles idempotency by checking this field before deciding to create vs. update.

### 1.6 Service Layer Design

**New file:** `app/api/services/calendar_service.py`

This module owns all Google Calendar API interactions. It never raises exceptions to callers — all errors are logged and a structured result dict is returned. Callers (Celery tasks) inspect the result and update the Assignment accordingly.

#### 1.6.1 `_build_calendar_service()`

```python
def _build_calendar_service():
    """
    Build and return an authenticated googleapiclient Resource object.
    
    Reads GOOGLE_SERVICE_ACCOUNT_JSON from settings, parses JSON,
    creates google.oauth2.service_account.Credentials with scope
    'https://www.googleapis.com/auth/calendar', then calls
    googleapiclient.discovery.build('calendar', 'v3', credentials=creds).
    
    Returns:
        googleapiclient Resource | None — None if credentials are missing
        or malformed (logs error, does not raise).
    """
```

Credentials are **not cached at module level** — each call creates fresh credentials. The service account token exchange is handled by the google-auth library automatically and is fast (no network call for the exchange itself; the JWT is signed locally). Module-level caching would cause issues if the env var changes between requests in development.

#### 1.6.2 `assignment_to_event_body(assignment: Assignment) -> dict`

```python
def assignment_to_event_body(assignment: Assignment) -> dict:
    """
    Convert an Assignment ORM instance to a Google Calendar event body dict.
    
    Reuses the timezone-mapping logic from services/calendar_sync/mapper.py
    (shared.constants.tz_for_state). The function is pure — no I/O.
    
    Event body includes:
    - summary: "[JHBridge] {service_type} — {src_lang} → {tgt_lang}"
    - description: assignment ID, client, interpreter, rate, notes
    - start/end with dateTime (ISO 8601) and timeZone from tz_for_state(state)
    - location: "{location}, {city}, {state} {zip_code}"
    - reminders: popup at 60 min and 15 min
    - attendees: [interpreter email] if interpreter is assigned
    - extendedProperties.private: {"assignment_id": str(assignment.id)}
      — this enables idempotency checks and future lookups by assignment ID
    
    Args:
        assignment: Assignment instance with all related objects pre-fetched.
    
    Returns:
        dict suitable for calendar.events().insert(body=...) or
        calendar.events().update(body=...).
    """
```

The `extendedProperties.private.assignment_id` field is the key idempotency anchor. If a sync task runs twice for the same assignment (e.g. due to Celery retry after a transient failure), the task first queries by this property to find existing events before creating a new one.

#### 1.6.3 `create_calendar_event(assignment: Assignment) -> dict`

```python
def create_calendar_event(assignment: Assignment) -> dict:
    """
    Create a new Google Calendar event for the assignment.
    
    Behavior:
    1. Build service via _build_calendar_service(); if None, return {'ok': False, 'error': 'not_configured'}
    2. Build event body via assignment_to_event_body()
    3. Call service.events().insert(calendarId=settings.GOOGLE_CALENDAR_ID, body=body).execute()
    4. On success: return {'ok': True, 'event_id': event['id'], 'html_link': event['htmlLink']}
    5. On HttpError 403: log "quota or permission error", return {'ok': False, 'error': 'permission'}
    6. On HttpError 429: log "rate limited", return {'ok': False, 'error': 'rate_limited'}
    7. On any other exception: log full traceback, return {'ok': False, 'error': 'unknown'}
    
    Args:
        assignment: Assignment instance.
    
    Returns:
        Result dict with 'ok' bool key.
    """
```

#### 1.6.4 `update_calendar_event(assignment: Assignment) -> dict`

```python
def update_calendar_event(assignment: Assignment) -> dict:
    """
    Update an existing Google Calendar event.
    
    Behavior:
    1. If assignment.gcal_event_id is None/blank, delegate to create_calendar_event()
    2. Build event body via assignment_to_event_body()
    3. Call service.events().update(
           calendarId=settings.GOOGLE_CALENDAR_ID,
           eventId=assignment.gcal_event_id,
           body=body
       ).execute()
    4. On HttpError 404 (event not found in calendar): attempt create instead,
       log warning "event {id} not found in calendar, recreating"
    5. Return same structure as create_calendar_event()
    
    Args:
        assignment: Assignment instance with gcal_event_id set.
    
    Returns:
        Result dict with 'ok' bool key.
    """
```

#### 1.6.5 `delete_calendar_event(event_id: str) -> dict`

```python
def delete_calendar_event(event_id: str) -> dict:
    """
    Delete a Google Calendar event by its event ID.
    
    Called when an assignment is cancelled or marked no-show.
    A 404 response is treated as success (event already gone).
    
    Args:
        event_id: Google Calendar event ID string.
    
    Returns:
        {'ok': True} on success or 404, {'ok': False, 'error': ...} otherwise.
    """
```

#### 1.6.6 `sync_assignment(assignment_id: int) -> dict`

```python
def sync_assignment(assignment_id: int) -> dict:
    """
    High-level sync orchestrator called by Celery tasks.
    
    Behavior:
    1. Fetch Assignment with select_related('interpreter__user', 'service_type',
       'source_language', 'target_language', 'client')
    2. If status is CANCELLED or NO_SHOW and gcal_event_id is set:
       → call delete_calendar_event(assignment.gcal_event_id)
       → on success update assignment: gcal_sync_status='DELETED', gcal_event_id=None
    3. If status is CANCELLED and gcal_event_id is None:
       → update gcal_sync_status='SKIPPED', return
    4. If gcal_event_id is set → call update_calendar_event()
    5. If gcal_event_id is None → call create_calendar_event()
    6. On result['ok'] == True:
       → assignment.gcal_event_id = result['event_id']
       → assignment.gcal_sync_status = 'SYNCED'
       → assignment.gcal_synced_at = timezone.now()
       → assignment.save(update_fields=['gcal_event_id', 'gcal_sync_status', 'gcal_synced_at'])
    7. On result['ok'] == False:
       → assignment.gcal_sync_status = 'FAILED'
       → assignment.save(update_fields=['gcal_sync_status'])
    8. Return result dict
    
    Args:
        assignment_id: Assignment primary key.
    
    Returns:
        Result dict from underlying create/update/delete call.
    """
```

### 1.7 Celery Task Design

**New file:** `app/tasks_calendar.py`

#### 1.7.1 `sync_assignment_to_calendar`

```python
@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    queue='calendar',
    acks_late=True,
)
def sync_assignment_to_calendar(self, assignment_id: int):
    """
    Async task: sync one assignment to Google Calendar.
    
    Trigger: called after any assignment status change that should be
    reflected in the calendar (CONFIRMED, updated, CANCELLED, NO_SHOW).
    
    Retry logic:
    - On 'rate_limited' error: retry with exponential backoff
      (delay = 60 * 2**self.request.retries seconds, max 5 attempts)
    - On 'permission' error: do NOT retry (misconfiguration); alert via
      logger.critical() so it surfaces in Railway logs
    - On 'unknown' error: retry with linear backoff
    - On Assignment.DoesNotExist: do not retry (log warning)
    
    After all retries exhausted: set gcal_sync_status='FAILED' and log
    a critical-level message so ops can investigate.
    """
```

#### 1.7.2 `bulk_backfill_calendar`

```python
@shared_task(bind=True, queue='calendar')
def bulk_backfill_calendar(self, assignment_ids: list[int] | None = None):
    """
    Periodic or one-shot task: sync all unsynced assignments.
    
    If assignment_ids is None, queries for all assignments where:
    - gcal_sync_status NOT IN ('SYNCED', 'SKIPPED', 'DELETED')
    - status IN ('PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED')
    
    Dispatches individual sync_assignment_to_calendar tasks for each
    with a 1-second countdown gap between them to avoid rate limit bursts
    (Google Calendar API limit: 1,000,000 queries/day but burst sensitive).
    
    This task is intentionally NOT periodic by default — it is triggered
    manually via management command or admin action.
    """
```

#### 1.7.3 `check_calendar_sync_health`

```python
@shared_task(queue='calendar')
def check_calendar_sync_health():
    """
    Periodic task (runs every 4 hours via Celery Beat).
    
    Finds assignments with gcal_sync_status='FAILED' and
    last update > 30 minutes ago, re-enqueues sync_assignment_to_calendar
    for each. Caps at 50 re-enqueues per run to avoid thundering herd.
    
    Celery Beat schedule entry in settings.py:
        'check-calendar-sync-health': {
            'task': 'app.tasks_calendar.check_calendar_sync_health',
            'schedule': crontab(minute=0, hour='*/4'),
        }
    """
```

### 1.8 Celery Queue Configuration

Add a dedicated `calendar` queue to `config/settings.py`:

```python
CELERY_TASK_ROUTES = {
    'app.tasks_calendar.*': {'queue': 'calendar'},
    # ... existing routes
}
```

Start the calendar queue worker separately in `Procfile`:

```
worker: celery -A config worker -l info -Q default
calendar_worker: celery -A config worker -l info -Q calendar --concurrency=2
```

Limiting concurrency to 2 on the calendar queue prevents concurrent API calls from triggering Google's burst rate limits.

### 1.9 Viewset Changes

**File:** `app/api/viewsets/assignments.py`

Replace the synchronous call `add_assignment_to_google_calendar(assignment.id)` in the `confirm` action with:

```python
from app.tasks_calendar import sync_assignment_to_calendar
sync_assignment_to_calendar.delay(assignment.id)
```

Add calendar sync dispatch to the following actions (they all modify assignment data that should be reflected in the calendar):

| Action | Trigger | Task behaviour |
|---|---|---|
| `confirm` | PENDING → CONFIRMED | Create event |
| `partial_update` / `update` | Any field update on CONFIRMED/IN_PROGRESS | Update event |
| `cancel` | → CANCELLED | Delete event |
| `no_show` | → NO_SHOW | Delete event |
| `complete` | → COMPLETED | Update event (mark as completed in description) |
| `reassign` | Interpreter changes | Update event (new attendee) |

In each action, dispatch the task **after** the database save, not before, so the task sees the final state.

### 1.10 Management Command for Bulk Backfill

**New file:** `app/management/commands/backfill_calendar.py`

```
python manage.py backfill_calendar
python manage.py backfill_calendar --status CONFIRMED --status IN_PROGRESS
python manage.py backfill_calendar --dry-run
python manage.py backfill_calendar --assignment-id 142
```

Behaviour:
- Queries assignments matching the specified statuses (default: CONFIRMED, IN_PROGRESS, COMPLETED)
- Excludes assignments with `gcal_sync_status=SYNCED` unless `--force` flag is passed
- In dry-run mode: prints a count and sample of what would be synced, makes no changes
- In live mode: calls `sync_assignment_to_calendar.apply_async(args=[a.id], countdown=i)` where `i` is the loop index — staggers dispatch by 1 second per assignment to avoid rate limit bursts
- Prints progress: `Dispatched {n} sync tasks. Monitor via: celery -A config inspect active`

### 1.11 Frontend: Sync Status Indicators in Dispatch Table

**File:** `adminfrontend/src/components/modules/DispatchModule.jsx`

Add a `gcal_sync_status` column to the dispatch table. The `AssignmentListSerializer` must be updated to include `gcal_sync_status` and `gcal_event_id`.

Indicator component (inline in DispatchModule or extracted to `shared/CalendarSyncBadge.jsx`):

| Status | Icon | Color | Tooltip |
|---|---|---|---|
| `SYNCED` | `CalendarCheck` (lucide) | `text-success` | "Synced to Google Calendar" |
| `PENDING` | `Clock` | `text-warning` | "Calendar sync pending" |
| `FAILED` | `CalendarX` | `text-destructive` | "Calendar sync failed — will retry" |
| `SKIPPED` | `Minus` | `text-muted-foreground` | "Not synced (skipped)" |
| `DELETED` | `CalendarOff` | `text-muted-foreground` | "Removed from calendar" |
| `null` | `CalendarDays` | `text-muted-foreground` | "Not yet synced" |

The column header should be `Cal` with the Google Calendar icon, 40px wide. Clicking the icon when status is FAILED or PENDING dispatches a manual re-sync via a new action endpoint `POST /api/v1/assignments/{id}/sync-calendar/`.

**New viewset action:**

```python
@action(detail=True, methods=['post'], url_path='sync-calendar')
def sync_calendar(self, request, pk=None):
    """Manually trigger calendar sync for an assignment. Admin only."""
    assignment = self.get_object()
    sync_assignment_to_calendar.delay(assignment.id)
    return Response({'detail': 'Calendar sync enqueued.', 'assignment_id': assignment.id})
```

Add `syncCalendar: (id) => api.post(\`/api/v1/assignments/${id}/sync-calendar/\`)` to `dispatchService.js`.

### 1.12 Timezone Gotchas

The existing `tz_for_state()` function in `shared/constants.py` maps US state codes to IANA timezone strings. This works for domestic US assignments but has two edge cases:

1. **Missing state code:** If `assignment.state` is blank or a full state name rather than a 2-letter code, `tz_for_state()` may return a wrong or empty value. The `assignment_to_event_body()` function must fall back to `settings.GOOGLE_CALENDAR_TIMEZONE` (default `America/New_York`) when the mapped timezone is None or empty.

2. **DST transitions:** The Google Calendar API respects IANA timezone DST rules when the event body specifies `timeZone` along with `dateTime`. Do NOT convert datetimes to UTC before sending — pass the local time with the IANA timezone and let Google handle DST. Django's `assignment.start_time` is stored as UTC (Django's default `USE_TZ=True` behaviour); convert with `start_time.astimezone(ZoneInfo(timezone_str)).isoformat()` before placing in the event body.

3. **Naive datetimes:** If any assignment `start_time` or `end_time` is naive (no tzinfo), do not pass it directly — `isoformat()` of a naive datetime produces a string without timezone offset, which the Google API rejects. Guard with `if assignment.start_time.tzinfo is None: raise ValueError(...)` and log an error, skip the sync.

### 1.13 Rate Limits

Google Calendar API default limits:
- 1,000,000 queries/day
- 500 queries/100 seconds per project
- Burst: unknown, but sustained >10 req/s causes 429s

Mitigation strategies already embedded in the design:
- Separate Celery queue with `--concurrency=2`
- 1-second stagger in bulk backfill
- Exponential backoff on 429 in `sync_assignment_to_calendar`
- `check_calendar_sync_health` caps re-enqueue at 50/run

### 1.14 Idempotency

The `extendedProperties.private.assignment_id` field written to every created event is the idempotency key. However, querying by extended properties requires a `privateExtendedProperty` query parameter — this has additional API cost. The simpler and preferred approach is:

1. Always check `assignment.gcal_event_id` first (most reliable)
2. Only query by `extendedProperties` in the backfill path when `gcal_event_id` is None but the assignment has already been confirmed (edge case: DB was rolled back after the sync task wrote the event ID)

### 1.15 Implementation Order for Initiative 1

1. Add pip dependencies to `requirements.txt`
2. Add env vars to `.env` and Railway dashboard
3. Add `gcal_event_id`, `gcal_sync_status`, `gcal_synced_at` to `Assignment` model + migration
4. Create `app/api/services/calendar_service.py` with all functions
5. Update `AssignmentListSerializer` to include calendar sync fields
6. Create `app/tasks_calendar.py` with all three tasks
7. Add `calendar` queue to Celery config and `Procfile`
8. Update `AssignmentViewSet` actions to dispatch tasks instead of calling service synchronously
9. Add `sync-calendar` viewset action
10. Create `app/management/commands/backfill_calendar.py`
11. Update `DispatchModule.jsx` to show sync status column
12. Add `syncCalendar` to `dispatchService.js`
13. Run `python manage.py backfill_calendar --dry-run` to verify
14. Run `python manage.py backfill_calendar` for initial sync

---

## Initiative 2 — Hiring Module

### 2.1 Overview

The current `HiringModule.jsx` is a pure mock showing the interpreter onboarding Kanban (6 onboarding phases: INVITED → COMPLETED). The Hiring Module is a separate, greenfield feature for recruiting *new* interpreters before they are onboarded. The pipeline is: **APPLIED → SCREENING → INTERVIEW → OFFER → HIRED / REJECTED**.

A HIRED applicant then enters the existing onboarding flow — the `ContractInvitation` model links the two systems.

### 2.2 Django Models

**New file:** `app/models/hiring.py`

#### 2.2.1 `JobPosting`

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `title` | CharField(max_length=200) | not null | e.g. "Medical Interpreter — Spanish" |
| `description` | TextField | not null | Markdown-compatible job description |
| `requirements` | TextField | blank=True | Bullet list of requirements |
| `languages` | ManyToManyField('Language') | blank=True | Required language pairs |
| `service_types` | ManyToManyField('ServiceType') | blank=True | Applicable service types |
| `location_type` | CharField(max_length=20, choices=LocationType) | default='BOTH' | IN_PERSON / REMOTE / BOTH |
| `status` | CharField(max_length=20, choices=PostingStatus) | default='DRAFT' | DRAFT / ACTIVE / PAUSED / CLOSED |
| `salary_min` | DecimalField(max_digits=8, decimal_places=2) | null, blank | Optional compensation range |
| `salary_max` | DecimalField(max_digits=8, decimal_places=2) | null, blank | |
| `application_deadline` | DateField | null, blank | If set, public form rejects after this date |
| `public_token` | UUIDField(default=uuid.uuid4, unique=True) | not null | Token for shareable public URL |
| `created_by` | ForeignKey('User', PROTECT) | not null | Admin who created it |
| `created_at` | DateTimeField(auto_now_add=True) | | |
| `updated_at` | DateTimeField(auto_now=True) | | |

```python
class PostingStatus(models.TextChoices):
    DRAFT  = 'DRAFT',  'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    CLOSED = 'CLOSED', 'Closed'

class LocationType(models.TextChoices):
    IN_PERSON = 'IN_PERSON', 'In Person'
    REMOTE    = 'REMOTE',    'Remote'
    BOTH      = 'BOTH',      'Both'
```

**Meta:**
```python
class Meta:
    db_table = 'app_jobposting'
    ordering = ['-created_at']
    indexes = [models.Index(fields=['status', 'application_deadline'])]
```

#### 2.2.2 `Applicant`

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `job_posting` | ForeignKey('JobPosting', PROTECT) | not null | |
| `first_name` | CharField(max_length=100) | not null | |
| `last_name` | CharField(max_length=100) | not null | |
| `email` | EmailField | not null | |
| `phone` | CharField(max_length=20) | blank | |
| `city` | CharField(max_length=100) | blank | |
| `state` | CharField(max_length=50) | blank | |
| `cover_letter` | TextField | blank | |
| `resume_s3_key` | CharField(max_length=500) | null, blank | S3 key for resume file |
| `resume_original_name` | CharField(max_length=255) | blank | Original filename for display |
| `additional_docs_s3_keys` | JSONField(default=list) | | List of S3 key strings for extra docs |
| `languages_spoken` | JSONField(default=list) | | List of language name strings from the form |
| `certifications` | JSONField(default=list) | | Self-reported certifications |
| `years_experience` | IntegerField | null, blank | |
| `referral_source` | CharField(max_length=100) | blank | How they heard about JHBridge |
| `stage` | CharField(max_length=20, choices=Stage) | default='APPLIED' | Current pipeline stage |
| `status` | CharField(max_length=20, choices=ApplicantStatus) | default='ACTIVE' | ACTIVE / REJECTED / HIRED / WITHDRAWN |
| `status_token` | UUIDField(default=uuid.uuid4, unique=True) | not null | Token for public status check URL |
| `internal_notes` | TextField | blank | Admin-only notes |
| `assigned_reviewer` | ForeignKey('User', SET_NULL, null, blank) | | Admin reviewing this applicant |
| `created_at` | DateTimeField(auto_now_add=True) | | Date application was received |
| `updated_at` | DateTimeField(auto_now=True) | | |

```python
class Stage(models.TextChoices):
    APPLIED    = 'APPLIED',    'Applied'
    SCREENING  = 'SCREENING',  'Screening'
    INTERVIEW  = 'INTERVIEW',  'Interview'
    OFFER      = 'OFFER',      'Offer'
    HIRED      = 'HIRED',      'Hired'
    REJECTED   = 'REJECTED',   'Rejected'

class ApplicantStatus(models.TextChoices):
    ACTIVE    = 'ACTIVE',    'Active'
    REJECTED  = 'REJECTED',  'Rejected'
    HIRED     = 'HIRED',     'Hired'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
```

**Meta:**
```python
class Meta:
    db_table = 'app_applicant'
    ordering = ['-created_at']
    indexes = [
        models.Index(fields=['stage', 'status']),
        models.Index(fields=['job_posting', 'stage']),
        models.Index(fields=['email']),
    ]
    unique_together = [('job_posting', 'email')]  # One application per posting per email
```

**Note on resume storage:** `resume_s3_key` stores the S3 key (not a full URL) so the key is portable across bucket renames and CDN configuration changes. Presigned URLs for download are generated on demand by the API.

#### 2.2.3 `ApplicantStageHistory`

Immutable audit trail. Never updated after creation.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `applicant` | ForeignKey('Applicant', CASCADE) | not null | |
| `from_stage` | CharField(max_length=20) | null, blank | Null for initial APPLIED entry |
| `to_stage` | CharField(max_length=20) | not null | |
| `changed_by` | ForeignKey('User', SET_NULL, null) | | Null for automated transitions |
| `reason` | TextField | blank | Admin-entered reason for rejection/advancement |
| `changed_at` | DateTimeField(auto_now_add=True) | | |

```python
class Meta:
    db_table = 'app_applicantstagehistory'
    ordering = ['changed_at']
```

#### 2.2.4 `Interview`

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `applicant` | ForeignKey('Applicant', CASCADE) | not null | |
| `interview_type` | CharField(max_length=20, choices=InterviewType) | not null | PHONE / VIDEO / IN_PERSON / PRACTICAL |
| `scheduled_at` | DateTimeField | not null | |
| `duration_minutes` | IntegerField | default=60 | |
| `location_or_link` | CharField(max_length=500) | blank | Room number or video link |
| `interviewer` | ForeignKey('User', SET_NULL, null) | | Admin conducting interview |
| `status` | CharField(max_length=20, choices=InterviewStatus) | default='SCHEDULED' | |
| `gcal_event_id` | CharField(max_length=255) | null, blank | Calendar event for the interview |
| `notes_before` | TextField | blank | Prep notes for interviewer |
| `notes_after` | TextField | blank | Post-interview notes |
| `outcome` | CharField(max_length=20, choices=InterviewOutcome) | null, blank | PASS / FAIL / MAYBE |
| `created_at` | DateTimeField(auto_now_add=True) | | |
| `updated_at` | DateTimeField(auto_now=True) | | |

```python
class InterviewType(models.TextChoices):
    PHONE      = 'PHONE',      'Phone Screen'
    VIDEO      = 'VIDEO',      'Video Call'
    IN_PERSON  = 'IN_PERSON',  'In Person'
    PRACTICAL  = 'PRACTICAL',  'Practical Assessment'

class InterviewStatus(models.TextChoices):
    SCHEDULED  = 'SCHEDULED',  'Scheduled'
    COMPLETED  = 'COMPLETED',  'Completed'
    CANCELLED  = 'CANCELLED',  'Cancelled'
    NO_SHOW    = 'NO_SHOW',    'No Show'

class InterviewOutcome(models.TextChoices):
    PASS  = 'PASS',  'Pass'
    FAIL  = 'FAIL',  'Fail'
    MAYBE = 'MAYBE', 'Maybe'
```

**Meta:**
```python
class Meta:
    db_table = 'app_interview'
    ordering = ['scheduled_at']
```

#### 2.2.5 `EvaluationRubric`

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `applicant` | OneToOneField('Applicant', CASCADE) | not null | One rubric per applicant |
| `language_proficiency` | IntegerField | null, blank | Score 1–5 |
| `communication_skills` | IntegerField | null, blank | Score 1–5 |
| `cultural_competency` | IntegerField | null, blank | Score 1–5 |
| `professionalism` | IntegerField | null, blank | Score 1–5 |
| `technical_knowledge` | IntegerField | null, blank | Score 1–5 (medical/legal terminology) |
| `reliability_indicators` | IntegerField | null, blank | Score 1–5 |
| `overall_recommendation` | CharField(max_length=20) | null, blank | STRONG_YES / YES / MAYBE / NO / STRONG_NO |
| `evaluator` | ForeignKey('User', SET_NULL, null) | | |
| `summary_notes` | TextField | blank | |
| `evaluated_at` | DateTimeField | null, blank | |
| `created_at` | DateTimeField(auto_now_add=True) | | |
| `updated_at` | DateTimeField(auto_now=True) | | |

**Computed property:**
```python
@property
def average_score(self):
    scores = [
        self.language_proficiency, self.communication_skills,
        self.cultural_competency, self.professionalism,
        self.technical_knowledge, self.reliability_indicators,
    ]
    filled = [s for s in scores if s is not None]
    return round(sum(filled) / len(filled), 2) if filled else None
```

**Meta:**
```python
class Meta:
    db_table = 'app_evaluationrubric'
```

#### 2.2.6 `OnboardingChecklist`

Only exists for HIRED applicants. Each item is stored as a JSON array of objects rather than separate model rows to keep the data model simple while allowing flexible customisation.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `applicant` | OneToOneField('Applicant', CASCADE) | not null | |
| `items` | JSONField(default=list) | | Array of `{id, label, completed, completed_at, completed_by_id}` |
| `contract_invitation` | ForeignKey('ContractInvitation', SET_NULL, null, blank) | | Link to existing onboarding system |
| `interpreter_account` | ForeignKey('User', SET_NULL, null, blank, related_name='hired_from') | | Set when interpreter account is created |
| `notes` | TextField | blank | |
| `created_at` | DateTimeField(auto_now_add=True) | | |
| `updated_at` | DateTimeField(auto_now=True) | | |

Default checklist items (populated by `hiring_service.create_onboarding_checklist`):

```python
DEFAULT_CHECKLIST_ITEMS = [
    {'id': 'background_check', 'label': 'Background check completed', 'completed': False},
    {'id': 'id_verified',      'label': 'Government ID verified',     'completed': False},
    {'id': 'certifications',   'label': 'Certifications verified',    'completed': False},
    {'id': 'contract_sent',    'label': 'Contract invitation sent',   'completed': False},
    {'id': 'contract_signed',  'label': 'Contract signed',            'completed': False},
    {'id': 'account_created',  'label': 'Interpreter account created','completed': False},
    {'id': 'orientation',      'label': 'Orientation completed',      'completed': False},
    {'id': 'first_assignment', 'label': 'First assignment assigned',  'completed': False},
]
```

**Meta:**
```python
class Meta:
    db_table = 'app_onboardingchecklist'
```

### 2.3 Model Registration

Add to `app/models/__init__.py`:
```python
from app.models.hiring import (
    JobPosting, Applicant, ApplicantStageHistory,
    Interview, EvaluationRubric, OnboardingChecklist,
)
```

Run `python manage.py makemigrations app`.

### 2.4 API Design

**New viewset file:** `app/api/viewsets/hiring.py`

Register in `app/api/urls.py`:
```python
from app.api.viewsets.hiring import JobPostingViewSet, ApplicantViewSet
router.register(r'hiring/job-postings', JobPostingViewSet, basename='job-posting')
router.register(r'hiring/applicants', ApplicantViewSet, basename='applicant')
```

Plus manual paths for public endpoints (no auth required).

#### 2.4.1 Complete Endpoint Table

| Method | URL | Action | Auth | Description |
|---|---|---|---|---|
| GET | `/api/v1/hiring/job-postings/` | list | Admin | List all postings with counts |
| POST | `/api/v1/hiring/job-postings/` | create | Admin | Create new posting |
| GET | `/api/v1/hiring/job-postings/{id}/` | retrieve | Admin | Full posting detail |
| PATCH | `/api/v1/hiring/job-postings/{id}/` | partial_update | Admin | Update posting |
| DELETE | `/api/v1/hiring/job-postings/{id}/` | destroy | Admin | Soft-delete (set status=CLOSED) |
| POST | `/api/v1/hiring/job-postings/{id}/activate/` | activate | Admin | Set status=ACTIVE |
| POST | `/api/v1/hiring/job-postings/{id}/pause/` | pause | Admin | Set status=PAUSED |
| POST | `/api/v1/hiring/job-postings/{id}/close/` | close | Admin | Set status=CLOSED |
| GET | `/api/v1/hiring/applicants/` | list | Admin | List applicants, filterable by stage/posting/status |
| GET | `/api/v1/hiring/applicants/{id}/` | retrieve | Admin | Full applicant detail |
| PATCH | `/api/v1/hiring/applicants/{id}/` | partial_update | Admin | Update internal notes, reviewer |
| POST | `/api/v1/hiring/applicants/{id}/advance/` | advance | Admin | Move to next stage |
| POST | `/api/v1/hiring/applicants/{id}/reject/` | reject | Admin | Move to REJECTED with reason |
| POST | `/api/v1/hiring/applicants/{id}/make-offer/` | make_offer | Admin | Move to OFFER stage |
| POST | `/api/v1/hiring/applicants/{id}/hire/` | hire | Admin | Move to HIRED, create checklist |
| GET | `/api/v1/hiring/applicants/{id}/timeline/` | timeline | Admin | Stage history + interview list |
| GET | `/api/v1/hiring/applicants/{id}/resume/` | resume | Admin | Generate presigned S3 URL for resume |
| POST | `/api/v1/hiring/applicants/{id}/interviews/` | create_interview | Admin | Schedule interview |
| PATCH | `/api/v1/hiring/applicants/{id}/interviews/{int_id}/` | update_interview | Admin | Update interview details or outcome |
| GET | `/api/v1/hiring/applicants/{id}/evaluation/` | get_evaluation | Admin | Get/create evaluation rubric |
| PUT | `/api/v1/hiring/applicants/{id}/evaluation/` | save_evaluation | Admin | Save evaluation scores |
| GET | `/api/v1/hiring/applicants/{id}/checklist/` | get_checklist | Admin | Get onboarding checklist |
| PATCH | `/api/v1/hiring/applicants/{id}/checklist/` | update_checklist | Admin | Toggle checklist item |
| GET | `/api/v1/hiring/kanban/` | kanban | Admin | All applicants grouped by stage with counts |
| GET | `/api/v1/hiring/stats/` | stats | Admin | Pipeline metrics (conversion rate, avg days per stage) |
| **Public** | | | | |
| GET | `/api/v1/public/jobs/` | public_list | Public | List ACTIVE postings (public fields only) |
| GET | `/api/v1/public/jobs/{token}/` | public_detail | Public | Single posting detail by public_token |
| POST | `/api/v1/public/jobs/{token}/apply/` | public_apply | Public | Submit application (multipart/form-data) |
| GET | `/api/v1/public/application-status/{status_token}/` | public_status | Public | Applicant self-service status check |

Public endpoints use `AllowAny` permission. They must be rate-limited with a custom throttle class (e.g. `AnonRateThrottle` at `10/hour` per IP).

### 2.5 Service Layer — `app/api/services/hiring_service.py`

#### `advance_stage(applicant: Applicant, new_stage: str, changed_by: User, reason: str = '') -> Applicant`

Validates the transition against the allowed pipeline (`APPLIED → SCREENING → INTERVIEW → OFFER → HIRED`). Creates an `ApplicantStageHistory` entry. Updates `applicant.stage`. Dispatches the appropriate Celery notification task. Returns the updated applicant.

Allowed transitions matrix:
```
APPLIED    → SCREENING
SCREENING  → INTERVIEW | REJECTED
INTERVIEW  → OFFER     | REJECTED
OFFER      → HIRED     | REJECTED
```
Any other transition raises `ValueError('Invalid stage transition')`.

#### `reject_applicant(applicant: Applicant, rejected_by: User, reason: str) -> Applicant`

Sets `applicant.stage = 'REJECTED'`, `applicant.status = 'REJECTED'`. Creates stage history entry. Dispatches `send_rejection_email` task. Returns applicant.

#### `hire_applicant(applicant: Applicant, hired_by: User) -> OnboardingChecklist`

1. Sets `applicant.stage = 'HIRED'`, `applicant.status = 'HIRED'`
2. Creates `ApplicantStageHistory(to_stage='HIRED')`
3. Creates `OnboardingChecklist(applicant=applicant, items=DEFAULT_CHECKLIST_ITEMS)`
4. Dispatches `send_offer_accepted_email` task
5. Returns the checklist

#### `create_onboarding_checklist(applicant: Applicant) -> OnboardingChecklist`

Creates a checklist with default items. Called by `hire_applicant`. Can be called independently if the checklist needs to be reset.

#### `schedule_interview(applicant: Applicant, data: dict, scheduled_by: User) -> Interview`

Creates an `Interview` instance. If `GOOGLE_CALENDAR_ID` is configured, dispatches `sync_interview_to_calendar` task (reuses Initiative 1's calendar service). Dispatches `send_interview_scheduled_email` to applicant. Returns interview.

#### `save_evaluation(applicant: Applicant, data: dict, evaluator: User) -> EvaluationRubric`

Creates or updates `EvaluationRubric` for the applicant. Sets `evaluator` and `evaluated_at = timezone.now()`. Returns the rubric.

#### `update_checklist_item(checklist: OnboardingChecklist, item_id: str, completed: bool, updated_by: User) -> OnboardingChecklist`

Finds the item in `checklist.items` by `id`, sets `completed`, `completed_at`, `completed_by_id`. Saves the checklist. Returns it.

When all items are completed and `checklist.contract_invitation` is None, dispatches `send_onboarding_complete_email`.

#### `process_public_application(posting: JobPosting, data: dict, resume_file, additional_files: list) -> Applicant`

1. Check `posting.status == 'ACTIVE'`; if not, raise `ValidationError`
2. Check `posting.application_deadline`: if past, raise `ValidationError('Application deadline passed')`
3. Check uniqueness: `Applicant.objects.filter(job_posting=posting, email=data['email']).exists()` → raise `ValidationError('Duplicate application')`
4. Upload resume to S3 via `TempStorage` or `MediaStorage` with key pattern `applicants/resumes/{uuid}_{original_name}`
5. Upload additional docs similarly; collect keys into list
6. Create `Applicant` with all data + S3 keys
7. Create initial `ApplicantStageHistory(from_stage=None, to_stage='APPLIED')`
8. Dispatch `send_application_received_email` to applicant
9. Dispatch `send_new_application_admin_email` to admin
10. Return applicant

#### `get_kanban_data() -> dict`

Returns all active applicants grouped by stage, including counts and key fields for card display. Uses a single queryset with `select_related('job_posting', 'assigned_reviewer')` and groups in Python to avoid N+1.

#### `get_pipeline_stats(posting_id: int | None = None) -> dict`

Returns: total applicants per stage, conversion rates between stages, average days spent in each stage (from `ApplicantStageHistory` timestamps), top rejection reasons.

#### `generate_resume_presigned_url(applicant: Applicant, expires_in: int = 3600) -> str`

Uses `boto3` to generate a presigned S3 GET URL for `applicant.resume_s3_key`. Returns the URL string.

### 2.6 Celery Tasks — `app/tasks_hiring.py`

| Task | Trigger | Queue | Retry |
|---|---|---|---|
| `send_application_received_email(applicant_id)` | Public application submitted | `default` | 3x |
| `send_new_application_admin_email(applicant_id)` | Public application submitted | `default` | 3x |
| `send_stage_advance_email(applicant_id, new_stage)` | Stage advanced | `default` | 3x |
| `send_rejection_email(applicant_id, reason)` | Applicant rejected | `default` | 3x |
| `send_interview_scheduled_email(interview_id)` | Interview scheduled | `default` | 3x |
| `send_interview_reminder_email(interview_id)` | Periodic check 24h before | `default` | 2x |
| `send_offer_accepted_email(applicant_id)` | Hired | `default` | 3x |
| `sync_interview_to_calendar(interview_id)` | Interview created/updated | `calendar` | 5x exponential |
| `check_stale_applicants()` | Periodic (daily at 9am) | `default` | 1x |

`check_stale_applicants` finds applicants in SCREENING or INTERVIEW stages with no activity for > 14 days and notifies the assigned reviewer.

### 2.7 Email Templates

All templates live in `templates/emails/hiring/`:

| Template | Subject | Recipients | Content |
|---|---|---|---|
| `application_received.html` | "We received your application — JHBridge" | Applicant | Application summary, status check URL (public_status_token link), timeline expectations |
| `new_application_admin.html` | "New Interpreter Application — {name}" | Admin team | Applicant name, posting title, application date, admin link |
| `screening_invite.html` | "Next Steps: Screening Call — JHBridge" | Applicant | Brief intro, what to expect in screening |
| `interview_scheduled.html` | "Interview Scheduled — JHBridge" | Applicant | Date/time, type, location/link, what to prepare |
| `interview_reminder.html` | "Reminder: Your Interview Tomorrow — JHBridge" | Applicant | Interview details, contact info if they need to reschedule |
| `rejection.html` | "Application Status Update — JHBridge" | Applicant | Warm rejection, encouragement to apply again, general feedback |
| `offer_letter.html` | "Welcome to JHBridge — Offer Letter" | Applicant | Offer summary, next steps, contract invitation will follow |
| `onboarding_complete.html` | "Onboarding Complete — JHBridge" | Admin + Interpreter | Checklist summary, interpreter is ready for assignments |

All templates extend `emails/base_email.html` (existing base template). No template hard-codes salaries or specific legal terms — those are written manually by admins if needed.

### 2.8 Public Application Form

**Public URL pattern:** `/apply/{posting_token}/` (Django template view — not part of the admin React frontend)
Alternatively served as a standalone React form at `adminfrontend/public/apply.html` if React is the preferred approach.

**Recommended approach:** serve via Django template for SEO and simplicity (no JS required for form submission). The existing `templates/public/` directory already holds public-facing Django templates.

**Django view:** `app/views/public_apply.py` — `PublicApplicationView` (FormView)

**File upload flow:**
1. Form uses `multipart/form-data` with `enctype="multipart/form-data"`
2. On submit, view calls `process_public_application()` from `hiring_service.py`
3. Resume and additional docs are passed as Django `InMemoryUploadedFile` or `TemporaryUploadedFile` objects
4. Service uploads to S3 using `boto3` directly (not via Django's `FileField.save()`) so the key is controlled explicitly: `applicants/{posting_id}/resumes/{uuid}_{sanitized_filename}`
5. File size limit: 10 MB for resume, 5 MB per additional doc, max 3 additional docs
6. Allowed types: PDF, DOCX, DOC for resume; PDF, JPG, PNG for additional docs (validated server-side by checking file magic bytes, not just extension)
7. On success: redirect to `/application-status/{status_token}/` with a success flash message
8. On error: re-render form with field-level errors

**Status check page:** `/application-status/{status_token}/` — reads `Applicant` by `status_token`, displays current stage, stage history timeline, interview dates (no sensitive details). Never requires login.

**Rate limiting:** Apply Django's `RateLimitMixin` or a custom decorator limiting to 3 submissions per IP per hour on the apply endpoint.

### 2.9 Serializers

**New file:** `app/api/serializers/hiring.py`

| Serializer | Model | Fields | Use |
|---|---|---|---|
| `JobPostingListSerializer` | JobPosting | id, title, status, language names, application_deadline, applicant_count (annotated), created_at | Table list |
| `JobPostingDetailSerializer` | JobPosting | All fields + languages, service_types, recent applicants count per stage | Detail/edit |
| `JobPostingCreateSerializer` | JobPosting | All writable fields; auto-generates public_token | Create/update |
| `ApplicantListSerializer` | Applicant | id, name, email, stage, status, job_posting_title, created_at, assigned_reviewer_name | Table list + Kanban cards |
| `ApplicantDetailSerializer` | Applicant | All fields + computed resume_url (presigned), stage history, interview list | Detail drawer |
| `ApplicantStageHistorySerializer` | ApplicantStageHistory | All fields + changed_by_name | Timeline |
| `InterviewSerializer` | Interview | All fields + interviewer_name | Create/list/update |
| `EvaluationRubricSerializer` | EvaluationRubric | All fields + average_score (read-only) | Evaluation form |
| `OnboardingChecklistSerializer` | OnboardingChecklist | id, applicant_id, items, contract_invitation_id, interpreter_account_id | Checklist tab |
| `PublicJobPostingSerializer` | JobPosting | title, description, requirements, location_type, languages, service_types, application_deadline | Public form |
| `PublicApplicationSerializer` | — (non-model) | first_name, last_name, email, phone, city, state, cover_letter, languages_spoken, certifications, years_experience, referral_source; resume file; additional_files | Public form validation |

### 2.10 Frontend Components

**File:** `adminfrontend/src/components/modules/HiringModule.jsx` (replace existing mock)

#### 2.10.1 `HiringModule` (root)

Props: none (all data from hooks)

State:
- `activeView`: `'kanban' | 'list' | 'stats'`
- `activePosting`: posting ID filter (null = all postings)
- `selectedApplicant`: applicant ID for detail drawer
- `showJobFormModal`: boolean
- `editingPosting`: posting object or null

Renders:
- `SectionHeader` with "Hiring Pipeline" title and "New Posting" button
- `TabBar` with views: Kanban | Applications List | Stats
- `PostingFilterBar` — dropdown of ACTIVE postings
- Conditionally renders `HiringKanbanBoard`, `HiringListView`, or `HiringStatsView`
- `ApplicantDetailDrawer` (always mounted, controlled by `selectedApplicant`)
- `JobPostingFormModal` (controlled by `showJobFormModal`)

Data: `useHiring()` custom hook wrapping all `hiringService.js` calls.

#### 2.10.2 `HiringKanbanBoard`

Props: `{ applicants, onCardClick, onStageChange, loading }`

Renders 5 columns: APPLIED / SCREENING / INTERVIEW / OFFER / HIRED. A sixth column "REJECTED" is shown only if `showRejected` toggle is active.

Each column:
- Header: stage label + count badge
- Scrollable card list
- Each card: applicant name, posting title, days in current stage (badge), evaluation score if available (star icon), assigned reviewer avatar

Cards are NOT draggable in v1 (drag-to-stage-advance creates accidental transitions — use the detail drawer action buttons instead).

#### 2.10.3 `ApplicantDetailDrawer`

Props: `{ applicantId, onClose, onStageChange }`

Tabs: **Profile | Documents | Interviews | Evaluation | Timeline**

**Profile tab:**
- Name, email, phone, location
- Languages spoken (chips)
- Certifications (chips)
- Years experience
- Referral source
- Cover letter (expandable)
- Internal notes (editable textarea for admins)
- Assigned reviewer (dropdown)

**Documents tab:**
- Resume: filename, upload date, "Download" button (calls `hiringService.getResumeUrl(id)` to get presigned URL, opens in new tab)
- Additional docs list with same pattern
- "No documents uploaded" empty state

**Interviews tab:**
- Timeline of past interviews with outcome badges
- "Schedule Interview" button → opens `InterviewSchedulerModal`
- Each interview card: type badge, date/time, interviewer name, outcome, post-interview notes

**Evaluation tab:**
- `EvaluationForm` component (see below)
- Read-only average score display
- Overall recommendation badge

**Timeline tab:**
- Chronological list of all `ApplicantStageHistory` entries
- Each entry: from/to stage, changed by, timestamp, reason
- Interview events interspersed in chronological order

**Action bar (bottom of drawer):**
- Advance to next stage button (disabled if already at HIRED/REJECTED)
- Reject button (opens reason modal)
- Make Offer button (visible at INTERVIEW stage)
- Hire button (visible at OFFER stage)

#### 2.10.4 `InterviewSchedulerModal`

Props: `{ applicantId, onSuccess, onClose }`

Fields:
- Interview type (select: Phone / Video / In Person / Practical)
- Date and time (datetime-local input)
- Duration (select: 30 / 45 / 60 / 90 min)
- Location or video link (text)
- Interviewer (select from admin users list)
- Prep notes (textarea)

On submit: calls `hiringService.scheduleInterview(applicantId, data)`. On success: shows toast "Interview scheduled", closes modal, refreshes applicant detail.

#### 2.10.5 `EvaluationForm`

Props: `{ applicantId, evaluation, onSave }`

A simple form with 6 score sliders (1–5) or star-rating inputs:
- Language Proficiency
- Communication Skills
- Cultural Competency
- Professionalism
- Technical Knowledge
- Reliability Indicators

Overall recommendation select: Strong Yes / Yes / Maybe / No / Strong No

Summary notes textarea.

"Save Evaluation" button calls `hiringService.saveEvaluation(applicantId, data)`.

Displays computed average score live as scores change.

#### 2.10.6 `JobPostingFormModal`

Props: `{ posting, onSuccess, onClose }` (posting is null for create)

Fields:
- Title
- Description (textarea — rich text not required in v1)
- Requirements (textarea)
- Languages (multi-select from `languageService.getLanguages()`)
- Service types (multi-select from `settingsService.getServiceTypes()`)
- Location type (radio: In Person / Remote / Both)
- Salary range (two number inputs, optional)
- Application deadline (date picker, optional)
- Status (select: Draft / Active)

On submit: create or update via `hiringService` methods.

#### 2.10.7 `OnboardingChecklist`

Props: `{ applicantId }`

Renders the checklist items as a list of checkboxes. Checking/unchecking calls `hiringService.updateChecklistItem(applicantId, itemId, completed)`. Shows completion percentage progress bar at top. Shows "Send Contract Invitation" button if `contract_invitation` is null and `contract_signed` item is not complete.

#### 2.10.8 `HiringStatsView`

Props: none (fetches from `hiringService.getStats()`)

Displays:
- KPI cards: Total applicants this month, conversion rate (applied→hired), avg days to hire, open postings
- Funnel chart (recharts `FunnelChart` or stacked bar): counts per stage
- Stage-by-stage conversion rate table
- Top rejection reasons (from stage history `reason` field frequency analysis)

### 2.11 `hiringService.js`

**New file:** `adminfrontend/src/services/hiringService.js`

```javascript
export const hiringService = {
  // Job Postings
  getJobPostings: (params = {}) => api.get('/api/v1/hiring/job-postings/', { params }),
  getJobPosting: (id) => api.get(`/api/v1/hiring/job-postings/${id}/`),
  createJobPosting: (data) => api.post('/api/v1/hiring/job-postings/', data),
  updateJobPosting: (id, data) => api.patch(`/api/v1/hiring/job-postings/${id}/`, data),
  activatePosting: (id) => api.post(`/api/v1/hiring/job-postings/${id}/activate/`),
  pausePosting: (id) => api.post(`/api/v1/hiring/job-postings/${id}/pause/`),
  closePosting: (id) => api.post(`/api/v1/hiring/job-postings/${id}/close/`),

  // Applicants
  getApplicants: (params = {}) => api.get('/api/v1/hiring/applicants/', { params }),
  getApplicant: (id) => api.get(`/api/v1/hiring/applicants/${id}/`),
  updateApplicant: (id, data) => api.patch(`/api/v1/hiring/applicants/${id}/`, data),
  advanceStage: (id, reason = '') => api.post(`/api/v1/hiring/applicants/${id}/advance/`, { reason }),
  rejectApplicant: (id, reason) => api.post(`/api/v1/hiring/applicants/${id}/reject/`, { reason }),
  makeOffer: (id) => api.post(`/api/v1/hiring/applicants/${id}/make-offer/`),
  hireApplicant: (id) => api.post(`/api/v1/hiring/applicants/${id}/hire/`),
  getTimeline: (id) => api.get(`/api/v1/hiring/applicants/${id}/timeline/`),
  getResumeUrl: (id) => api.get(`/api/v1/hiring/applicants/${id}/resume/`),

  // Interviews
  scheduleInterview: (applicantId, data) =>
    api.post(`/api/v1/hiring/applicants/${applicantId}/interviews/`, data),
  updateInterview: (applicantId, interviewId, data) =>
    api.patch(`/api/v1/hiring/applicants/${applicantId}/interviews/${interviewId}/`, data),

  // Evaluation
  getEvaluation: (applicantId) =>
    api.get(`/api/v1/hiring/applicants/${applicantId}/evaluation/`),
  saveEvaluation: (applicantId, data) =>
    api.put(`/api/v1/hiring/applicants/${applicantId}/evaluation/`, data),

  // Checklist
  getChecklist: (applicantId) =>
    api.get(`/api/v1/hiring/applicants/${applicantId}/checklist/`),
  updateChecklistItem: (applicantId, itemId, completed) =>
    api.patch(`/api/v1/hiring/applicants/${applicantId}/checklist/`, { item_id: itemId, completed }),

  // Aggregate
  getKanban: (params = {}) => api.get('/api/v1/hiring/kanban/', { params }),
  getStats: (params = {}) => api.get('/api/v1/hiring/stats/', { params }),
};
```

### 2.12 Implementation Order

1. Create `app/models/hiring.py` with all 6 models
2. Add exports to `app/models/__init__.py`
3. Run `python manage.py makemigrations app && python manage.py migrate`
4. Create `app/api/serializers/hiring.py`
5. Create `app/api/services/hiring_service.py` with all service functions
6. Create `app/tasks_hiring.py` with email tasks (calendar tasks come after Initiative 1)
7. Create `app/api/viewsets/hiring.py` — admin endpoints first
8. Register viewsets in `app/api/urls.py`
9. Create public application Django view + template
10. Create status check Django view + template
11. Add throttle classes for public endpoints
12. Create `adminfrontend/src/services/hiringService.js`
13. Create `HiringKanbanBoard.jsx`
14. Create `ApplicantDetailDrawer.jsx` with all tabs
15. Create `InterviewSchedulerModal.jsx`
16. Create `EvaluationForm.jsx`
17. Create `JobPostingFormModal.jsx`
18. Create `OnboardingChecklist.jsx`
19. Create `HiringStatsView.jsx`
20. Rewrite `HiringModule.jsx` to wire everything together
21. Add `HiringModule` route to `App.jsx` navigation

### 2.13 Gotchas

1. **Duplicate application prevention:** The `unique_together = [('job_posting', 'email')]` constraint is the database-level guard, but the service layer should check before attempting insert and return a user-friendly error message to the public form, not a raw Django 500.

2. **Resume file upload on public form:** Django's default `FILE_UPLOAD_MAX_MEMORY_SIZE` (2.5 MB) may cause large resumes to be written to disk as `TemporaryUploadedFile`. The S3 upload in `process_public_application` must handle both `InMemoryUploadedFile` and `TemporaryUploadedFile` (both implement the file-like interface — pass the `.file` attribute to boto3's `upload_fileobj`).

3. **Stage transition validation in the API:** The `advance_stage` service function validates transitions, but the viewset action `advance` does not know which stage the applicant will move to (it advances to the next stage automatically). If an applicant is at OFFER and the admin clicks "Advance", the service must know that OFFER advances to HIRED, not another intermediate stage. Document this explicitly: the `advance` action always moves to the next stage in the sequence; use `hire`, `make-offer`, `reject` for specific target stages.

4. **Calendar sync for interviews:** The `Interview` model has a `gcal_event_id` field. Syncing interview calendar events reuses the calendar service from Initiative 1. However, the event body format for interviews differs from assignments — create a separate `interview_to_event_body(interview)` function in `calendar_service.py`.

5. **OnboardingChecklist → ContractInvitation link:** When the admin clicks "Send Contract Invitation" from the checklist view, it creates a `ContractInvitation` (existing model in `app/models/contracts.py`) and links it back to the `OnboardingChecklist.contract_invitation` field. Do not re-invent the contract flow — reuse the existing `ContractInvitation` model and email templates.

6. **File security on resume download:** The presigned URL endpoint (`GET /hiring/applicants/{id}/resume/`) must verify the caller is an admin before generating the presigned URL. The URL itself is unauthenticated (S3 presigned) but has a short expiry (3600 seconds). Never expose `resume_s3_key` directly in the serializer — always serve via the presigned URL endpoint.

7. **The existing HiringModule mock shows onboarding phases (INVITED → COMPLETED) not the hiring pipeline (APPLIED → HIRED).** The new HiringModule replaces this completely. The existing onboarding Kanban functionality should be moved to the `InterpretersModule.jsx` or a dedicated `OnboardingModule.jsx` — confirm with stakeholders before deleting the mock data.

---

## Initiative 3 — Finance & Accounting Module

### 3.1 Overview

The existing `FinanceModule.jsx` is almost entirely mocked. The backend `FinanceViewSet` is functional for invoices and expenses but lacks: line-item detail on invoices, manual revenue entry, Google Workspace export, and a complete frontend integration.

`financeService.js` does not exist. All finance API calls from the frontend currently go nowhere.

This initiative covers three layers:
1. New Django models (InvoiceLineItem, DriveExport)
2. New and extended backend endpoints
3. Google Workspace service layer (Drive, Sheets, Slides)
4. Complete frontend rewrite of FinanceModule.jsx
5. financeService.js (new file)

### 3.2 New Models

**File:** `app/models/finance.py` (append to existing)

#### 3.2.1 `InvoiceLineItem`

The existing `Invoice` model stores only `subtotal` and `total` — there is no line-item detail. This model adds that detail.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `invoice` | ForeignKey('Invoice', CASCADE, related_name='line_items') | not null | |
| `description` | CharField(max_length=500) | not null | Line item description |
| `quantity` | DecimalField(max_digits=8, decimal_places=2) | default=1 | Hours, units, etc. |
| `unit` | CharField(max_length=50) | default='hour' | hour / session / page / unit |
| `unit_price` | DecimalField(max_digits=10, decimal_places=2) | not null | Price per unit |
| `assignment` | ForeignKey('Assignment', SET_NULL, null, blank) | | Optional link to source assignment |
| `sort_order` | IntegerField | default=0 | Display order |

**Computed:**
```python
@property
def line_total(self):
    return self.quantity * self.unit_price
```

**Meta:**
```python
class Meta:
    db_table = 'app_invoicelineitem'
    ordering = ['sort_order', 'id']
```

The existing `Invoice.subtotal` field is now treated as a **computed field** that sums `line_items.line_total`. In practice, `subtotal` on the model is still stored (denormalized for query performance) and updated whenever line items change. An `Invoice.recalculate_totals()` method handles this:

```python
def recalculate_totals(self):
    self.subtotal = sum(item.line_total for item in self.line_items.all())
    self.total = self.subtotal + self.tax_amount
    self.save(update_fields=['subtotal', 'total'])
```

Call `recalculate_totals()` in the `InvoiceLineItem` post-save signal.

#### 3.2.2 `DriveExport`

Tracks every file pushed to Google Drive.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | AutoField | PK | |
| `file_id` | CharField(max_length=255) | not null | Google Drive file ID |
| `file_url` | URLField(max_length=500) | not null | `https://drive.google.com/file/d/{id}/view` |
| `file_type` | CharField(max_length=50, choices=FileType) | not null | INVOICE_PDF / PAY_STUB / CONTRACT / ANALYTICS_SHEET / PAYROLL_SHEET / EXEC_SLIDES |
| `drive_folder_id` | CharField(max_length=255) | blank | Parent folder ID in Drive |
| `s3_key` | CharField(max_length=500) | blank | Source S3 key (empty for Sheets/Slides) |
| `content_type_id` | ForeignKey(ContentType, SET_NULL, null) | | Django ContentType for generic FK |
| `object_id` | PositiveIntegerField | null, blank | PK of the related object |
| `related_object` | GenericForeignKey('content_type_id', 'object_id') | | Invoice, PayrollDocument, etc. |
| `exported_by` | ForeignKey('User', SET_NULL, null) | | |
| `exported_at` | DateTimeField(auto_now_add=True) | | |
| `expires_at` | DateTimeField | null, blank | For documents that should be refreshed periodically |
| `is_stale` | BooleanField | default=False | True when S3 source was updated after export |

```python
class FileType(models.TextChoices):
    INVOICE_PDF      = 'INVOICE_PDF',      'Invoice PDF'
    PAY_STUB         = 'PAY_STUB',         'Pay Stub'
    CONTRACT         = 'CONTRACT',         'Contract'
    ANALYTICS_SHEET  = 'ANALYTICS_SHEET',  'Analytics Sheet'
    PAYROLL_SHEET    = 'PAYROLL_SHEET',    'Payroll Sheet'
    EXEC_SLIDES      = 'EXEC_SLIDES',      'Executive Report Slides'
```

**Meta:**
```python
class Meta:
    db_table = 'app_driveexport'
    ordering = ['-exported_at']
    indexes = [
        models.Index(fields=['file_type', 'exported_at']),
        models.Index(fields=['content_type_id', 'object_id']),
    ]
```

### 3.3 New API Endpoints

All under `/api/v1/finance/`. New endpoints extend the existing `FinanceViewSet`.

| Method | URL | Action | Description |
|---|---|---|---|
| GET | `/api/v1/finance/invoices/{id}/line-items/` | `invoice_line_items` | List line items for an invoice |
| POST | `/api/v1/finance/invoices/{id}/line-items/` | `create_line_item` | Add a line item |
| PATCH | `/api/v1/finance/invoices/{id}/line-items/{li_id}/` | `update_line_item` | Update a line item |
| DELETE | `/api/v1/finance/invoices/{id}/line-items/{li_id}/` | `delete_line_item` | Remove a line item (recalculates totals) |
| POST | `/api/v1/finance/invoices/{id}/generate-pdf/` | `generate_pdf` | Generate invoice PDF → save to S3 → return S3 URL |
| POST | `/api/v1/finance/invoices/{id}/export-to-drive/` | `export_invoice_to_drive` | Enqueue Drive export task, return DriveExport record |
| GET | `/api/v1/finance/revenue/` | `revenue_list` | List FinancialTransaction(type=INCOME) records |
| POST | `/api/v1/finance/revenue/` | `create_revenue` | Create manual revenue entry |
| GET | `/api/v1/finance/client-payments/` | `client_payments_list` | List ClientPayment records |
| POST | `/api/v1/finance/client-payments/` | `create_client_payment` | Record a client payment |
| GET | `/api/v1/finance/interpreter-payments/` | `interpreter_payments_list` | List InterpreterPayment records |
| PATCH | `/api/v1/finance/interpreter-payments/{id}/` | `update_interpreter_payment` | Update status/method |
| POST | `/api/v1/finance/interpreter-payments/{id}/process/` | `process_interpreter_payment` | Mark as PROCESSING |
| POST | `/api/v1/finance/interpreter-payments/{id}/complete/` | `complete_interpreter_payment` | Mark as COMPLETED |
| GET | `/api/v1/finance/drive-exports/` | `drive_exports_list` | List all DriveExport records |
| POST | `/api/v1/finance/analytics/export-to-sheets/` | `export_analytics_to_sheets` | Enqueue Sheets export, return DriveExport |
| POST | `/api/v1/finance/reports/generate-slides/` | `generate_executive_slides` | Enqueue Slides generation, return DriveExport |
| GET | `/api/v1/finance/analytics/summary/` | Alias of existing `summary` | Already exists |
| GET | `/api/v1/finance/analytics/pnl/` | Alias of existing `pnl` | Already exists |

### 3.4 New Serializers

**File:** `app/api/serializers/finance.py` (append)

| Serializer | Purpose |
|---|---|
| `InvoiceLineItemSerializer` | CRUD for line items; includes `line_total` read-only computed field |
| `InvoiceWithLineItemsSerializer` | Extends `InvoiceDetailSerializer` with nested `line_items` array |
| `FinancialTransactionSerializer` | For manual revenue entry (type=INCOME); writable |
| `RevenueEntryCreateSerializer` | Simplified: amount, description, date, notes; auto-sets type=INCOME, created_by from request |
| `ClientPaymentCreateSerializer` | Create client payment record |
| `InterpreterPaymentUpdateSerializer` | Update status, payment_method, notes |
| `DriveExportSerializer` | Read-only; file_id, file_url, file_type, exported_at, related object summary |

### 3.5 Google Workspace Service Layer

**New file:** `app/api/services/google_workspace_service.py`

This is the single, unified module for all Google Workspace API interactions (Drive, Sheets, Slides). It never imports Django models — callers pass primitive data or file-like objects. This keeps the service testable in isolation.

#### 3.5.1 Authentication

```python
def _build_drive_service():
    """
    Build an authenticated Google Drive API v3 service using the service account.
    Reads GOOGLE_SERVICE_ACCOUNT_JSON from settings.
    Scopes: ['https://www.googleapis.com/auth/drive']
    Returns googleapiclient Resource or None on error.
    """

def _build_sheets_service():
    """
    Build an authenticated Google Sheets API v4 service.
    Scope: 'https://www.googleapis.com/auth/spreadsheets'
    Returns googleapiclient Resource or None.
    """

def _build_slides_service():
    """
    Build an authenticated Google Slides API v1 service.
    Scope: 'https://www.googleapis.com/auth/presentations'
    Returns googleapiclient Resource or None.
    """
```

Use separate service instances per API because the scopes differ. In production, all three APIs are accessible from the same service account — just add all three scopes to the credential creation call:

```python
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
]
```

#### 3.5.2 Required Environment Variables for Workspace

| Variable | Description |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | (Same as Initiative 1 — reuse the same service account) |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | ID of the "JHBridge" root folder in Drive (created once manually, then shared with service account) |
| `GOOGLE_EXEC_SLIDES_TEMPLATE_ID` | Drive file ID of the master Slides template |
| `GOOGLE_SHEETS_ANALYTICS_FOLDER_ID` | Drive folder ID for analytics sheets |

#### 3.5.3 Drive Functions

**`get_or_create_folder(parent_id: str, name: str) -> str`**

Query Drive for a folder with the given name under `parent_id`. Returns its ID if found. Creates it if not found. This is idempotent — safe to call multiple times with the same args.

Implementation: `service.files().list(q=f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false").execute()`. If `files` list is empty, call `service.files().create(body={...})`.

Cache folder IDs in Django's cache backend (Redis) with a 24-hour TTL keyed by `drive_folder:{parent_id}:{name}` to avoid redundant API calls on repeated exports.

**`get_client_folder_id(client_name: str) -> str`**

Returns the Drive folder ID for `JHBridge / Clients / {client_name}`, creating the hierarchy if needed. Calls `get_or_create_folder` recursively.

**`get_interpreter_folder_id(interpreter_name: str) -> str`**

Same pattern: `JHBridge / Interpreters / {interpreter_name}`.

**Folder hierarchy:**
```
JHBridge (root, GOOGLE_DRIVE_ROOT_FOLDER_ID)
├── Clients/
│   └── {Client Company Name}/
│       └── Invoices/
├── Interpreters/
│   └── {Interpreter Full Name}/
│       └── Pay Stubs/
├── Analytics/
│   └── {YYYY-MM} Reports/
└── Executive Reports/
```

**`export_pdf_to_drive(pdf_bytes: bytes, filename: str, folder_id: str, description: str = '') -> dict`**

Uploads PDF bytes to Drive in the specified folder. Returns `{'file_id': ..., 'file_url': ..., 'web_view_link': ...}`.

Implementation: use `googleapiclient.http.MediaInMemoryUpload(pdf_bytes, mimetype='application/pdf')`, then `service.files().create(body={name, parents, description}, media_body=media_upload, fields='id,webViewLink,webContentLink').execute()`.

**`update_drive_file(file_id: str, pdf_bytes: bytes) -> dict`**

Update the content of an existing Drive file. Called when an invoice is re-generated after edits.

Implementation: `service.files().update(fileId=file_id, media_body=MediaInMemoryUpload(...)).execute()`.

**`share_with_email(file_id: str, email: str, role: str = 'reader') -> bool`**

Grants the specified email address access to a Drive file. Role options: `reader`, `commenter`, `writer`. Returns True on success.

Implementation: `service.permissions().create(fileId=file_id, body={'type': 'user', 'role': role, 'emailAddress': email}).execute()`.

**`delete_drive_file(file_id: str) -> bool`**

Moves file to trash. Called when a DriveExport record becomes stale and needs replacement.

#### 3.5.4 Sheets Functions

**`export_to_sheets(sheet_title: str, headers: list[str], rows: list[list], existing_sheet_id: str | None = None) -> dict`**

**Design decision: overwrite approach for analytics, new sheet for payroll.**

For analytics reports (P&L, revenue by service, etc.): the function overwrites a **designated "live" sheet per report type**. The `existing_sheet_id` parameter is used if a sheet already exists for this report type. This avoids creating dozens of sheets and makes the Finance team's bookmarks stable.

For payroll summaries: always create a new sheet per payroll period. Payroll is a point-in-time record and should not be overwritten.

Implementation:
1. If `existing_sheet_id` is None: `service.spreadsheets().create(body={'properties': {'title': sheet_title}}).execute()` → get `spreadsheetId`
2. If `existing_sheet_id` is set: clear existing data with `service.spreadsheets().values().clear(spreadsheetId=existing_sheet_id, range='A:ZZZ').execute()`
3. Write headers and rows via `service.spreadsheets().values().batchUpdate(body={...}).execute()`
4. Apply header formatting (bold, background color) via `service.spreadsheets().batchUpdate(body={requests: [...]}).execute()`

Returns `{'sheet_id': ..., 'sheet_url': ..., 'title': ...}`.

**`get_or_create_analytics_sheet(report_type: str, period_label: str) -> str`**

Looks up `DriveExport.objects.filter(file_type='ANALYTICS_SHEET').filter(object_id__metadata__report_type=report_type).order_by('-exported_at').first()` to find an existing sheet. If found and not stale, returns its `file_id`. Otherwise creates a new one.

#### 3.5.5 Slides Functions

**`generate_executive_slides(period_start: date, period_end: date) -> dict`**

Generates a monthly executive report presentation. Returns `{'presentation_id': ..., 'presentation_url': ..., 'file_id': ...}`.

Implementation:
1. **Copy the master template:** `drive_service.files().copy(fileId=settings.GOOGLE_EXEC_SLIDES_TEMPLATE_ID, body={'name': f'JHBridge Executive Report — {period_label}'}).execute()` → get new presentation ID
2. **Collect data:** query the finance models to get KPIs, P&L, top clients, interpreter utilization for the period
3. **Replace placeholders:** use `slides_service.presentations().batchUpdate(presentationId=new_id, body={'requests': [...]}).execute()` with `replaceAllText` requests for each `{{PLACEHOLDER}}`
4. **Move to Executive Reports folder** using `drive_service.files().update(fileId=new_id, addParents=exec_folder_id, removeParents='root').execute()`

**Slides included in the template and their placeholders:**

| Slide | Title | Placeholders |
|---|---|---|
| 1 | KPI Summary | `{{PERIOD}}`, `{{TOTAL_REVENUE}}`, `{{NET_PROFIT}}`, `{{PROFIT_MARGIN}}`, `{{TOTAL_ASSIGNMENTS}}`, `{{ACTIVE_INTERPRETERS}}` |
| 2 | P&L Chart | `{{PNL_CHART_MONTH_1}}` … `{{PNL_CHART_MONTH_12}}` (text table, not a real chart — Slides API doesn't support chart data injection easily) |
| 3 | Top Clients | `{{CLIENT_1_NAME}}`, `{{CLIENT_1_REVENUE}}` … (top 5) |
| 4 | Interpreter Utilization | `{{UTILIZATION_RATE}}`, `{{AVG_HOURS_PER_INTERPRETER}}`, `{{TOP_INTERPRETER}}` |
| 5 | Outlook | `{{UPCOMING_ASSIGNMENTS_COUNT}}`, `{{OUTSTANDING_INVOICES_AMOUNT}}`, `{{PENDING_PAYMENTS_COUNT}}` |

**Note on chart injection:** The Google Slides API does not support updating chart data directly for embedded Sheets charts unless the chart is explicitly linked to a Sheet. For the P&L slide, use a text-based table layout in the template instead of a chart — this is simpler and more reliable.

**`share_presentation_with_team(presentation_id: str, emails: list[str]) -> bool`**

Shares the presentation with a list of emails (admin/management team). Uses `share_with_email` from Drive functions.

#### 3.5.6 Invoice PDF Generation

**New function in** `app/api/services/invoice_service.py`:

**`generate_invoice_pdf(invoice: Invoice) -> bytes`**

Uses `reportlab` (already in `requirements.txt`) to generate a professional invoice PDF. Returns raw bytes.

Layout:
- Company header (logo from S3, name, address, phone, email)
- "INVOICE" title with invoice number and status badge
- Bill To: client company name, address, contact
- Issued date, due date, payment terms
- Line items table: Description | Quantity | Unit | Unit Price | Total
- Subtotal, Tax, **Total** rows
- Notes section
- Payment instructions

**`save_invoice_pdf_to_s3(invoice: Invoice, pdf_bytes: bytes) -> str`**

Saves PDF bytes to S3 using `ContractStorage` (or a new `InvoiceStorage` class if invoices need their own bucket). Key: `invoices/{invoice.invoice_number}.pdf`. Returns S3 key. Updates `invoice.pdf_file` field with the key.

### 3.6 Celery Tasks for Finance — `app/tasks_finance.py`

| Task | Trigger | Queue | Retry | Description |
|---|---|---|---|---|
| `generate_and_upload_invoice_pdf(invoice_id)` | Invoice send action or manual generate | `default` | 3x | Calls `generate_invoice_pdf` + `save_invoice_pdf_to_s3` + updates `Invoice.pdf_file` |
| `export_invoice_to_drive(invoice_id, user_id)` | Admin clicks "Export to Drive" | `default` | 3x | Fetches PDF from S3, calls `export_pdf_to_drive`, creates `DriveExport` record |
| `export_paystub_to_drive(payroll_id, user_id)` | Admin exports payroll doc | `default` | 3x | Same pattern as invoice |
| `export_pnl_to_sheets(period_start, period_end, user_id)` | Admin clicks "Export P&L to Sheets" | `default` | 3x | Queries P&L data, calls `export_to_sheets`, creates `DriveExport` |
| `export_payroll_summary_to_sheets(period_start, period_end, user_id)` | Payroll period close | `default` | 3x | Queries payroll data, calls `export_to_sheets` with new sheet |
| `generate_monthly_executive_report(year, month)` | Celery Beat: 1st of each month at 8am | `default` | 2x | Calls `generate_executive_slides`, creates `DriveExport`, shares with admin emails |
| `mark_overdue_invoices()` | Celery Beat: daily at 6am | `default` | 1x | Queries Invoice with `due_date < today` and `status=SENT`, sets `status=OVERDUE` |
| `send_invoice_email(invoice_id)` | Invoice send action | `default` | 3x | Emails invoice PDF to client (attach or link) |
| `send_payment_reminder(invoice_id)` | Already triggered by `remind_invoice` action | `default` | 3x | Sends reminder email to client |

### 3.7 Frontend Finance Module — Complete Rewrite

**File:** `adminfrontend/src/components/modules/FinanceModule.jsx`

The rewrite adds a "Revenue" tab and converts all mocked data to live API calls via `financeService.js`.

#### 3.7.1 Tab Structure

```
[Overview] [Invoices] [Expenses] [Revenue] [Interpreter Payments] [Reports]
```

The "Interpreter Payments" tab is new (not in the current mock). The existing mock has Overview, Invoices, Expenses, Reports.

#### 3.7.2 Overview Tab

**KPI Cards (from `GET /api/v1/finance/summary/`):**

| Card | Metric | Sub-text |
|---|---|---|
| MTD Revenue | `mtd_revenue` | vs prior month % change (computed frontend-side from P&L data) |
| MTD Expenses | `mtd_expenses` | vs prior month |
| Net Profit | `mtd_revenue - mtd_expenses` | Margin % |
| Outstanding | `outstanding_invoices` | Count from invoice list |
| Pending Payments | `pending_interpreter_payments` | To interpreters |

**P&L Chart:**
- `recharts LineChart` with two lines: Revenue and Expenses
- Data from `GET /api/v1/finance/analytics/pnl/` (12-month data)
- X-axis: month labels (Jan, Feb …)
- Y-axis: dollar amounts formatted with `$` prefix
- Tooltip shows Revenue, Expenses, Profit for each month

**Revenue Breakdown:**
- `recharts PieChart` with data from `GET /api/v1/finance/analytics/revenue-by-service/`
- Legend below chart

**Top Clients:**
- Table from `GET /api/v1/finance/analytics/revenue-by-client/`
- Columns: Rank, Client Name, Missions, Revenue

**Quick Actions:**
- "Create Invoice" button → opens `InvoiceFormModal`
- "Record Revenue" button → opens `RevenueEntryModal`
- "Add Expense" button → opens `ExpenseFormModal`

#### 3.7.3 Invoices Tab

**Table columns:** Invoice # | Client | Amount | Status | Issued | Due | Actions

**Status badge colors:**
- DRAFT: muted
- SENT: info
- PAID: success
- OVERDUE: destructive
- CANCELLED: muted
- DISPUTED: warning

**Row actions (via dropdown ⋮):**
- View → opens `InvoiceDetailDrawer`
- Send (DRAFT only) → `financeService.sendInvoice(id)` + toast
- Mark Paid (SENT/OVERDUE) → opens payment method dialog → `financeService.markPaid(id, method)`
- Send Reminder (SENT/OVERDUE) → `financeService.remindInvoice(id)` + toast
- Generate PDF → `financeService.generatePdf(id)` → shows loading spinner → opens presigned URL in new tab
- Export to Drive → `financeService.exportToDrive(id)` → shows toast "Export enqueued"
- Cancel (DRAFT/SENT) → confirmation dialog → `financeService.cancelInvoice(id)`

**Create Invoice Modal (`InvoiceFormModal`):**

Fields:
- Client (searchable dropdown of clients)
- Due Date (date picker)
- Tax Rate % (number, default 0)
- Line Items (dynamic list):
  - Each row: Description | Quantity | Unit | Unit Price | [computed] Total | Delete button
  - "Add Line Item" button adds a new empty row
  - Line items auto-calculate subtotal live
- Notes (textarea)
- Payment terms (textarea, pre-filled from settings)

On submit: `POST /api/v1/finance/invoices/` (creates invoice header) then `POST /api/v1/finance/invoices/{id}/line-items/` for each line item.

**Invoice Detail Drawer:**

Sections:
- Header: Invoice number, status badge, client name, amounts
- Line items table (read-only if status ≠ DRAFT)
- Payment history (ClientPayment records linked to this invoice)
- Drive exports history (DriveExport records for this invoice)
- Timeline: created, sent, reminder sent dates
- "Edit" button (DRAFT only) → inline edit mode

#### 3.7.4 Expenses Tab

**Table columns:** ID | Type | Amount | Description | Status | Date Incurred | Date Paid | Actions

**Row actions:**
- View detail → drawer (shows receipt if uploaded)
- Approve (PENDING) → `financeService.approveExpense(id)`
- Pay (APPROVED) → `financeService.payExpense(id)`
- Delete (PENDING only)

**Create Expense Modal:**

Fields:
- Expense Type (select: Operational / Administrative / Marketing / Salary / Tax / Other)
- Amount
- Description
- Date Incurred (date picker)
- Receipt upload (file, optional) — uploaded to S3 via presigned upload URL before form submit
- Notes

#### 3.7.5 Revenue Tab

**Left panel — Manual Revenue Entry Form:**

Fields:
- Amount
- Description
- Date (date picker, defaults to today)
- Notes
- Source (optional: assignment link, client link, or "other")

Submit: `POST /api/v1/finance/revenue/` → `FinancialTransaction(type=INCOME)` record.

**Right panel — Income Transaction List:**

Table: Date | Amount | Description | Source | Actions

Filter bar: date range, min/max amount.

Pagination: same `StandardPagination` as other tables.

#### 3.7.6 Interpreter Payments Tab

**Table columns:** Ref # | Interpreter | Assignment | Amount | Method | Status | Scheduled | Actions

**Row actions:**
- View detail
- Mark Processing (PENDING) → `financeService.processInterpreterPayment(id)`
- Mark Completed (PROCESSING) → `financeService.completeInterpreterPayment(id)`
- Export Pay Stub to Drive → `financeService.exportPayStubToDrive(payrollId)`

**Filters:** Status, Interpreter, Date range.

#### 3.7.7 Reports Tab

**Period selector:** Month/Year dropdowns, or date range picker.

**Report type selector (radio/tabs):**
- P&L Summary
- Revenue by Service
- Revenue by Client
- Revenue by Language
- Expense Breakdown
- Payroll Summary

**Export destination buttons (shown after selecting type):**

| Button | Action |
|---|---|
| Download PDF | Generates a PDF report client-side using `jsPDF` + recharts `toDataURL()`, or calls a backend `generate-report-pdf` endpoint. Downloads directly. |
| Export to Sheets | `financeService.exportToSheets(reportType, periodStart, periodEnd)` → toast "Export enqueued — check Drive exports list" |
| Export to Drive | `financeService.exportToDrive(reportType, periodStart, periodEnd)` → same pattern |
| Generate Slides | `financeService.generateExecutiveSlides(year, month)` → toast "Generating executive report…" |

**Drive Exports History list:**

Table below the export buttons: File Type | Filename | Exported At | Drive Link | Stale indicator

Data from `GET /api/v1/finance/drive-exports/`.

Clicking Drive Link opens `file_url` in a new tab.

### 3.8 `financeService.js`

**New file:** `adminfrontend/src/services/financeService.js`

```javascript
import api from './api';

export const financeService = {
  // ── Summary & Analytics ────────────────────────────────────────
  getSummary: () => api.get('/api/v1/finance/summary/'),
  getPnl: (params = {}) => api.get('/api/v1/finance/analytics/pnl/', { params }),
  getRevenueByService: (params = {}) =>
    api.get('/api/v1/finance/analytics/revenue-by-service/', { params }),
  getRevenueByClient: (params = {}) =>
    api.get('/api/v1/finance/analytics/revenue-by-client/', { params }),
  getRevenueByLanguage: (params = {}) =>
    api.get('/api/v1/finance/analytics/revenue-by-language/', { params }),

  // ── Invoices ───────────────────────────────────────────────────
  getInvoices: (params = {}) => api.get('/api/v1/finance/invoices/', { params }),
  getInvoice: (id) => api.get(`/api/v1/finance/invoices/${id}/`),
  createInvoice: (data) => api.post('/api/v1/finance/invoices/', data),
  sendInvoice: (id) => api.post(`/api/v1/finance/invoices/${id}/send/`),
  markPaid: (id, payment_method) =>
    api.post(`/api/v1/finance/invoices/${id}/mark-paid/`, { payment_method }),
  remindInvoice: (id) => api.post(`/api/v1/finance/invoices/${id}/remind/`),
  cancelInvoice: (id) => api.post(`/api/v1/finance/invoices/${id}/cancel/`),
  generatePdf: (id) => api.post(`/api/v1/finance/invoices/${id}/generate-pdf/`),
  exportInvoiceToDrive: (id) => api.post(`/api/v1/finance/invoices/${id}/export-to-drive/`),

  // ── Invoice Line Items ─────────────────────────────────────────
  getLineItems: (invoiceId) =>
    api.get(`/api/v1/finance/invoices/${invoiceId}/line-items/`),
  createLineItem: (invoiceId, data) =>
    api.post(`/api/v1/finance/invoices/${invoiceId}/line-items/`, data),
  updateLineItem: (invoiceId, lineItemId, data) =>
    api.patch(`/api/v1/finance/invoices/${invoiceId}/line-items/${lineItemId}/`, data),
  deleteLineItem: (invoiceId, lineItemId) =>
    api.delete(`/api/v1/finance/invoices/${invoiceId}/line-items/${lineItemId}/`),

  // ── Expenses ───────────────────────────────────────────────────
  getExpenses: (params = {}) => api.get('/api/v1/finance/expenses/', { params }),
  createExpense: (data) => api.post('/api/v1/finance/expenses/', data),
  approveExpense: (id) => api.post(`/api/v1/finance/expenses/${id}/approve/`),
  payExpense: (id) => api.post(`/api/v1/finance/expenses/${id}/pay/`),

  // ── Revenue (manual income entries) ───────────────────────────
  getRevenue: (params = {}) => api.get('/api/v1/finance/revenue/', { params }),
  createRevenue: (data) => api.post('/api/v1/finance/revenue/', data),

  // ── Client Payments ────────────────────────────────────────────
  getClientPayments: (params = {}) =>
    api.get('/api/v1/finance/client-payments/', { params }),
  createClientPayment: (data) => api.post('/api/v1/finance/client-payments/', data),

  // ── Interpreter Payments ───────────────────────────────────────
  getInterpreterPayments: (params = {}) =>
    api.get('/api/v1/finance/interpreter-payments/', { params }),
  updateInterpreterPayment: (id, data) =>
    api.patch(`/api/v1/finance/interpreter-payments/${id}/`, data),
  processInterpreterPayment: (id) =>
    api.post(`/api/v1/finance/interpreter-payments/${id}/process/`),
  completeInterpreterPayment: (id) =>
    api.post(`/api/v1/finance/interpreter-payments/${id}/complete/`),

  // ── Drive Exports ──────────────────────────────────────────────
  getDriveExports: (params = {}) =>
    api.get('/api/v1/finance/drive-exports/', { params }),
  exportPayStubToDrive: (payrollId) =>
    api.post(`/api/v1/finance/payroll/${payrollId}/export-to-drive/`),

  // ── Reports / Workspace ────────────────────────────────────────
  exportToSheets: (reportType, periodStart, periodEnd) =>
    api.post('/api/v1/finance/analytics/export-to-sheets/', {
      report_type: reportType,
      period_start: periodStart,
      period_end: periodEnd,
    }),
  generateExecutiveSlides: (year, month) =>
    api.post('/api/v1/finance/reports/generate-slides/', { year, month }),
};
```

### 3.9 Implementation Order for Finance

1. **Models:** Add `InvoiceLineItem` and `DriveExport` to `app/models/finance.py` → migration
2. **Serializers:** Add `InvoiceLineItemSerializer`, `DriveExportSerializer`, `RevenueEntryCreateSerializer` to `app/api/serializers/finance.py`
3. **Invoice service:** Add `generate_invoice_pdf` and `save_invoice_pdf_to_s3` to `app/api/services/invoice_service.py`
4. **FinanceViewSet:** Add all new endpoints (line items, revenue, client/interpreter payments, drive exports, PDF generation)
5. **Google Workspace service:** Create `app/api/services/google_workspace_service.py` with Drive functions (start with Drive, then Sheets, then Slides)
6. **Celery tasks:** Create `app/tasks_finance.py` — start with `mark_overdue_invoices` and `generate_and_upload_invoice_pdf` (these are independent of Google Workspace)
7. **Add workspace tasks** to `app/tasks_finance.py` after Drive/Sheets/Slides service layer is tested
8. **Frontend:** Create `financeService.js`
9. **Overview tab:** Wire KPI cards + P&L chart + Revenue breakdown
10. **Invoices tab:** Table + row actions + `InvoiceFormModal` with line items
11. **Expenses tab:** Table + row actions + `ExpenseFormModal`
12. **Revenue tab:** Manual entry form + income list
13. **Interpreter Payments tab:** Table + row actions
14. **Reports tab:** Selectors + export buttons + DriveExport history list
15. **Invoice detail drawer:** Full detail with line items table and Drive export history
16. **Celery Beat schedule:** Add `mark_overdue_invoices` and `generate_monthly_executive_report` to `CELERY_BEAT_SCHEDULE` in settings
17. **Test PDF generation** with a real invoice before wiring the Drive export
18. **Test Drive export** manually with a single invoice before adding all the other export types

### 3.10 Gotchas for Finance

1. **Invoice total consistency:** The `Invoice.subtotal` field and the sum of `InvoiceLineItem.line_total` values can diverge if a line item is added/updated without calling `recalculate_totals()`. The safest approach is a `post_save` signal on `InvoiceLineItem` that calls `invoice.recalculate_totals()`. The signal must disconnect itself during `recalculate_totals()` execution to avoid infinite recursion.

2. **Google Drive file sharing:** The service account creates Drive files but by default **only the service account can view them**. To make a file accessible to a real human (admin, client), the `share_with_email` function must be called explicitly. Never assume a file is accessible just because the upload succeeded.

3. **Drive API quota:** The Drive API has a limit of 12,000 requests per 60 seconds (very generous). The more likely throttle is the `insert` operation for file creation — limit bulk exports to one file per second in Celery task concurrency settings.

4. **`DriveExport` staleness:** When an invoice is edited after it has been exported to Drive, the Drive copy is now stale. Set `DriveExport.is_stale = True` in an `Invoice.post_save` signal whenever the invoice is modified after `paid_date` is None (i.e., it's still in a mutable state). The frontend should show a "Stale" warning badge on the Drive Exports history row.

5. **Invoice PDF generation with reportlab:** `reportlab` renders pages in points (72 points = 1 inch). Letter size is 612 × 792 points. Always test the PDF with long client names, many line items (overflow to next page), and Unicode characters (Haitian Creole, Somali, Spanish). reportlab handles Unicode well when using a Unicode-compatible font (e.g., `DejaVuSans`) — do not use the default Helvetica for any user-generated content.

6. **Slides template management:** The `GOOGLE_EXEC_SLIDES_TEMPLATE_ID` must be stored in a Drive folder the service account can access. If the template is updated by a human admin (editing slide layout), the new version takes effect on the next `generate_executive_slides` call automatically. However, adding or removing `{{PLACEHOLDERS}}` requires a code change in `generate_executive_slides`. Document the placeholder list and version it.

7. **P&L data period boundaries:** The existing `pnl` endpoint uses `timedelta(days=365)` which is not the same as 12 calendar months (it skips/doubles Feb 29, and the months shift each year). Replace with a proper 12-month range using `dateutil.relativedelta` or a loop over the last 12 calendar months by year+month.

8. **`FinancialTransaction` vs `ClientPayment` as revenue source:** The existing analytics queries use `ClientPayment(status='COMPLETED')` as the revenue source, not `FinancialTransaction(type='INCOME')`. Manual revenue entries created via the new `/finance/revenue/` endpoint create `FinancialTransaction(type='INCOME')` records directly. The analytics endpoints must be updated to SUM both sources, or all manual revenue entries must also create a `ClientPayment` record (simpler but less clean). **Recommended:** query both sources and combine in the service layer. Update all analytics functions in `analytics_service.py` to include `FinancialTransaction` INCOME records in total revenue calculations.

---

## Appendix A: Environment Variable Reference (All Initiatives)

| Variable | Initiative | Required | Notes |
|---|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 1 + 3 | Yes (for both) | Shared service account; add all scopes |
| `GOOGLE_CALENDAR_ID` | 1 | Yes | Company calendar ID |
| `GOOGLE_CALENDAR_TIMEZONE` | 1 | Yes | Default timezone e.g. `America/New_York` |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | 3 | Yes | JHBridge root Drive folder |
| `GOOGLE_EXEC_SLIDES_TEMPLATE_ID` | 3 | Yes | Master Slides template file ID |
| `GOOGLE_SHEETS_ANALYTICS_FOLDER_ID` | 3 | Yes | Drive folder for analytics sheets |
| `FASTAPI_BASE_URL` | 1 (remove) | No | Delete after Initiative 1 is deployed |

## Appendix B: New pip Dependencies Summary

| Package | Initiative | Purpose |
|---|---|---|
| `google-api-python-client>=2.100.0` | 1 + 3 | Google Calendar, Drive, Sheets, Slides API client |
| `google-auth>=2.23.0` | 1 + 3 | Service account credential handling |
| `google-auth-httplib2>=0.1.1` | 1 + 3 | HTTP transport for google-auth |

No other new pip packages are required. All other dependencies (reportlab, boto3, celery, redis, DRF) are already in `requirements.txt`.

## Appendix C: Migration Checklist

Run in this order after each initiative:

```bash
# After Initiative 1
python manage.py makemigrations app --name "add_gcal_sync_fields_to_assignment"
python manage.py migrate

# After Initiative 2
python manage.py makemigrations app --name "add_hiring_models"
python manage.py migrate

# After Initiative 3
python manage.py makemigrations app --name "add_invoice_line_items_and_drive_export"
python manage.py migrate
```

Always run migrations in a transaction on MySQL. Railway's deploy pipeline should run `python manage.py migrate` before the new code starts serving traffic.

## Appendix D: FastAPI Sidecar Retirement

After Initiative 1 is fully deployed and the Celery calendar tasks are confirmed working in production:

1. Remove `FASTAPI_BASE_URL` from all environments
2. Remove the `sync_assignment` import from `app/api/viewsets/assignments.py` (old function)
3. Archive the `services/calendar_sync/` directory to `_archive/` (do not delete — useful reference)
4. Remove the FastAPI service from `Procfile` and Railway service configuration
5. Remove `requests` call from `app/api/services/assignment_service.py` (`add_assignment_to_google_calendar` function) — replace with a comment pointing to the new Celery task
6. Update `services/requirements.txt` deprecation note

**Do not retire the sidecar until the Celery task has been running in production for at least one full business week with zero FAILED sync statuses.**
```

---

This document contains **10 major sections**, **3 appendices**, and is approximately **1,050 lines** of detailed markdown. Below is the section count:

1. Shared Conventions
2. Initiative 1 — Google Calendar Full Sync (sections 1.1–1.15)
3. Initiative 2 — Hiring Module (sections 2.1–2.13)
4. Initiative 3 — Finance & Accounting Module (sections 3.1–3.10)
5. Appendix A — Environment Variables
6. Appendix B — pip Dependencies
7. Appendix C — Migration Checklist
8. Appendix D — FastAPI Sidecar Retirement

**Important:** This is a READ-ONLY planning session. The file was NOT written to disk. To save it, copy the markdown block above (everything between the triple-backtick fences) and paste it into `IMPLEMENTATION_PLAN.md` at the path:

`c:\Users\dace\Desktop\workspace\Jhventure\jhbridge\codebase\legacy\legacy\IMPLEMENTATION_PLAN.md`

Or run this from a terminal:

```bash
# From the project root
# Paste the content into a new file using your editor of choice
code IMPLEMENTATION_PLAN.md
```

### Critical Files for Implementation

- `/c/Users/dace/Desktop/workspace/Jhventure/jhbridge/codebase/legacy/legacy/app/models/services.py` - Assignment model to add `gcal_event_id`, `gcal_sync_status`, `gcal_synced_at` fields; also the reference for all Assignment status constants and methods
- `/c/Users/dace/Desktop/workspace/Jhventure/jhbridge/codebase/legacy/legacy/app/api/services/assignment_service.py` - Contains the synchronous `add_assignment_to_google_calendar` that must be removed and replaced; also contains the `assignment_to_calendar_event` mapper logic to reuse
- `/c/Users/dace/Desktop/workspace/Jhventure/jhbridge/codebase/legacy/legacy/app/api/viewsets/finance.py` - All existing finance endpoints to extend with line items, revenue, Drive export, and new analytics endpoints
- `/c/Users/dace/Desktop/workspace/Jhventure/jhbridge/codebase/legacy/legacy/app/models/finance.py` - Existing `Invoice` model (subtotal/total structure to understand before adding InvoiceLineItem) and all other finance models; also where `DriveExport` and `InvoiceLineItem` will be added
- `/c/Users/dace/Desktop/workspace/Jhventure/jhbridge/codebase/legacy/legacy/adminfrontend/src/components/modules/FinanceModule.jsx` - Current mock to replace; establishes the tab structure and component naming conventions for the full rewrite